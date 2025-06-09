from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import os.path
import pickle
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple, List

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = 'Asia/Kolkata'
SEARCH_WINDOW_DAYS = 365  # Standard search window of 1 year

def get_ist_time() -> datetime:
    """Get current time in IST"""
    return datetime.now(ZoneInfo(TIMEZONE))

def ensure_ist_timezone(dt: datetime) -> datetime:
    """Ensure datetime is in IST timezone"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo(TIMEZONE))
    return dt.astimezone(ZoneInfo(TIMEZONE))

def get_calendar_service() -> Tuple[Any, str]:
    """Authenticate and get Google Calendar service"""
    creds = None
    calendar_id = None

    try:
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)

        # First, try to find an existing calendar
        calendar_list = service.calendarList().list().execute().get('items', [])
        for calendar in calendar_list:
            if calendar['summary'] == 'Python Calendar':
                calendar_id = calendar['id']
                break

        # If no existing calendar found, create a new one
        if not calendar_id:
            new_calendar = {
                'summary': 'Python Calendar',
                'timeZone': TIMEZONE
            }
            created_calendar = service.calendars().insert(body=new_calendar).execute()
            calendar_id = created_calendar['id']
            print("Created new calendar with ID:", calendar_id)
        else:
            print("Using existing calendar with ID:", calendar_id)
        
        return service, calendar_id
        
    except Exception as e:
        print(f"Error in authentication: {str(e)}")
        return None, None

def get_events(service, calendar_id: str, event_name: Optional[str] = None, 
              start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Get events from calendar based on name and/or date range"""
    try:
        # Get current time in IST
        current_time = get_ist_time()
        
        # If no dates provided, use a wider time range for name-only searches
        if not start_date and not end_date:
            if event_name:
                # For name-only searches, look in a wider time range
                start_date = current_time - timedelta(days=SEARCH_WINDOW_DAYS)
                end_date = current_time + timedelta(days=SEARCH_WINDOW_DAYS)
            else:
                # For date-only searches, default to today
                start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            print(f"Original start_date: {start_date}")
            print(f"Original end_date: {end_date}")
            
            # Ensure dates are in IST
            if start_date:
                start_date = ensure_ist_timezone(start_date)
                print(f"Ensured IST timezone for start_date: {start_date}")
            
            if end_date:
                end_date = ensure_ist_timezone(end_date)
                print(f"Ensured IST timezone for end_date: {end_date}")
            
            # If only start_date is provided, set end_date to end of that day
            if start_date and not end_date:
                end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                print(f"Set end_date to end of day: {end_date}")
            
            # If only end_date is provided, set start_date to beginning of that day
            elif end_date and not start_date:
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                print(f"Set start_date to start of day: {start_date}")
            
            # Add buffer time to ensure we catch all events
            start_date = start_date - timedelta(minutes=5)
            end_date = end_date + timedelta(minutes=5)
            print(f"Final search window: {start_date} to {end_date}")
            
        time_min = start_date.isoformat()
        time_max = end_date.isoformat()
        
        print(f"Searching events from {time_min} to {time_max}")
        print(f"Using calendar ID: {calendar_id}")
        
        # Get all events in the time range
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500  # Increase max results to ensure we get all events
        ).execute()
        
        events = events_result.get('items', [])
        print(f"Found {len(events)} total events in time range")
        
        # Filter by name if provided
        if event_name:
            # Case-insensitive search and partial match
            events = [
                event for event in events 
                if event_name.lower() in event.get('summary', '').lower()
            ]
            print(f"Found {len(events)} events matching name '{event_name}'")
            
        # Print details of found events for debugging
        for event in events:
            print(f"Event: {event.get('summary')} at {event.get('start')}")
            
        return events
        
    except Exception as e:
        print(f"Error getting events: {str(e)}")
        return []

def create_event(service, calendar_id: str, event_details: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new event in the specified calendar"""
    try:
        # Ensure all datetime fields are in IST
        if 'start' in event_details:
            if isinstance(event_details['start'], dict):
                if 'dateTime' in event_details['start']:
                    # Convert to IST if timezone is not specified or is different
                    dt = datetime.fromisoformat(event_details['start']['dateTime'].replace('Z', '+00:00'))
                    dt = ensure_ist_timezone(dt)
                    event_details['start']['dateTime'] = dt.isoformat()
                event_details['start']['timeZone'] = TIMEZONE
                
        if 'end' in event_details:
            if isinstance(event_details['end'], dict):
                if 'dateTime' in event_details['end']:
                    # Convert to IST if timezone is not specified or is different
                    dt = datetime.fromisoformat(event_details['end']['dateTime'].replace('Z', '+00:00'))
                    dt = ensure_ist_timezone(dt)
                    event_details['end']['dateTime'] = dt.isoformat()
                event_details['end']['timeZone'] = TIMEZONE
            
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_details
        ).execute()
        
        return {
            "success": True,
            "message": f"Event created successfully: {created_event['id']}",
            "created_event": created_event
        }
        
    except Exception as e:
        error_msg = f"Error creating event: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "created_event": None
        }

def update_event(service, calendar_id: str, updated_details: Dict[str, Any],
                event_name: Optional[str] = None, event_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Update an existing event in the specified calendar by either name or date"""
    try:
        if not event_name and not event_date:
            return {
                "success": False,
                "message": "Error: Either event_name or event_date must be provided",
                "updated_event": None
            }
            
        # Get current time in IST
        current_time = get_ist_time()
            
        # Search for the event
        start_date = None
        end_date = None
        if event_date:
            print(f"Original event_date: {event_date}")
            
            # Ensure date is in IST
            event_date = ensure_ist_timezone(event_date)
            print(f"Ensured IST timezone: {event_date}")
            
            # Set search window to ±5 minutes around the event date
            start_date = event_date - timedelta(minutes=5)
            end_date = event_date + timedelta(minutes=5)
            print(f"Search window: {start_date} to {end_date}")
            
            # If no time component in the date, search the entire day
            if event_date.hour == 0 and event_date.minute == 0:
                start_date = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = event_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                print(f"Full day search: {start_date} to {end_date}")
        else:
            # If only searching by name, use a wider time range
            start_date = current_time - timedelta(days=SEARCH_WINDOW_DAYS)
            end_date = current_time + timedelta(days=SEARCH_WINDOW_DAYS)
        
        # Search for the event
        events = get_events(
            service,
            calendar_id,
            event_name=event_name,
            start_date=start_date,
            end_date=end_date
        )
        
        if not events:
            search_criteria = []
            if event_name:
                search_criteria.append(f"name '{event_name}'")
            if event_date:
                search_criteria.append(f"date {event_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            return {
                "success": False,
                "message": f"No event found with {', '.join(search_criteria)}",
                "updated_event": None
            }
            
        event = events[0]
        event_id = event['id']
        
        # Start with the existing event details
        updated_event_body = {
            'summary': event.get('summary', ''),
            'start': event.get('start', {}),
            'end': event.get('end', {}),
            'description': event.get('description', ''),
            'location': event.get('location', '')
        }
        
        # Update only the fields that are provided and not None in updated_details
        for key, value in updated_details.items():
            if value is not None:  # Only update if the value is not None
                if key in ['start', 'end'] and isinstance(value, dict):
                    # Handle timezone for start/end times
                    if 'dateTime' in value:
                        # Convert to IST if timezone is not specified or is different
                        dt = datetime.fromisoformat(value['dateTime'].replace('Z', '+00:00'))
                        dt = ensure_ist_timezone(dt)
                        value['dateTime'] = dt.isoformat()
                    value['timeZone'] = TIMEZONE
                    updated_event_body[key] = value
                else:
                    updated_event_body[key] = value
            else:
                # If value is None, remove the field from the body
                updated_event_body.pop(key, None)
        
        # Ensure timezone is set for start and end times if they exist
        if 'start' in updated_event_body and updated_event_body['start']:
            updated_event_body['start']['timeZone'] = TIMEZONE
        if 'end' in updated_event_body and updated_event_body['end']:
            updated_event_body['end']['timeZone'] = TIMEZONE
            
        # Remove any None values from the body
        updated_event_body = {k: v for k, v in updated_event_body.items() if v is not None}
        
        # Ensure required fields are present
        if 'start' not in updated_event_body or not updated_event_body['start']:
            updated_event_body['start'] = event.get('start', {})
        if 'end' not in updated_event_body or not updated_event_body['end']:
            updated_event_body['end'] = event.get('end', {})
            
        print(f"Updating event with body: {updated_event_body}")
            
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=updated_event_body
        ).execute()
        
        return {
            "success": True,
            "message": f"Event updated successfully: {updated_event['id']}",
            "updated_event": updated_event
        }
        
    except Exception as e:
        error_msg = f"Error updating event: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "updated_event": None
        }

def delete_event(service, calendar_id: str, 
                event_name: Optional[str] = None, event_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Delete an event from the specified calendar by either name or date"""
    try:
        if not event_name and not event_date:
            return {
                "success": False,
                "message": "Error: Either event_name or event_date must be provided",
                "deleted_event": None
            }
            
        # Get current time in IST
        current_time = get_ist_time()
        
        # Handle date-based search
        start_date = None
        end_date = None
        if event_date:
            print(f"Original event_date: {event_date}")
            
            # If event_date is a string, parse it
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                except ValueError as e:
                    return {
                        "success": False,
                        "message": f"Invalid date format: {str(e)}",
                        "deleted_event": None
                    }
            
            # Ensure date is in IST
            event_date = ensure_ist_timezone(event_date)
            print(f"Ensured IST timezone: {event_date}")
            
            # Set search window to ±5 minutes around the event date
            start_date = event_date - timedelta(minutes=5)
            end_date = event_date + timedelta(minutes=5)
            print(f"Search window: {start_date} to {end_date}")
            
            # If no time component in the date, search the entire day
            if event_date.hour == 0 and event_date.minute == 0:
                start_date = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = event_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                print(f"Full day search: {start_date} to {end_date}")
        else:
            # If only searching by name, use a wider time range
            start_date = current_time - timedelta(days=SEARCH_WINDOW_DAYS)
            end_date = current_time + timedelta(days=SEARCH_WINDOW_DAYS)
        
        # Search for the event
        events = get_events(
            service,
            calendar_id,
            event_name=event_name,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"Found {len(events)} events in search window")
        
        if not events:
            search_criteria = []
            if event_name:
                search_criteria.append(f"name '{event_name}'")
            if event_date:
                search_criteria.append(f"date {event_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            return {
                "success": False,
                "message": f"No event found with {', '.join(search_criteria)}",
                "deleted_event": None
            }
            
        # Get the first matching event
        event = events[0]
        event_id = event['id']
        
        print(f"Found event: {event.get('summary')} at {event.get('start')}")
        
        # Delete the event
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # Prepare success message
        success_msg = "Event deleted successfully: "
        if event_name:
            success_msg += f"'{event_name}'"
        if event_date:
            if event_name:
                success_msg += " at "
            success_msg += f"{event_date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            
        return {
            "success": True,
            "message": success_msg,
            "deleted_event": {
                "id": event_id,
                "summary": event.get('summary'),
                "start": event.get('start'),
                "end": event.get('end')
            }
        }
        
    except Exception as e:
        error_msg = f"Error deleting event: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "deleted_event": None
        }

def get_all_events(service, calendar_id: str) -> List[Dict[str, Any]]:
    """Get all events from the calendar"""
    try:
        # Get current time in IST
        current_time = get_ist_time()
        
        # Set a wide time range to get all events
        start_date = current_time - timedelta(days=SEARCH_WINDOW_DAYS)
        end_date = current_time + timedelta(days=SEARCH_WINDOW_DAYS)
        
        time_min = start_date.isoformat()
        time_max = end_date.isoformat()
        
        print(f"Retrieving all events from {time_min} to {time_max}")
        print(f"Using calendar ID: {calendar_id}")
        
        # Get all events in the time range
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500  # Maximum allowed by the API
        ).execute()
        
        events = events_result.get('items', [])
        print(f"Found {len(events)} total events")
        
        return events
        
    except Exception as e:
        print(f"Error getting all events: {str(e)}")
        return []

def main():
    """Main function to demonstrate calendar operations"""
    service, calendar_id = get_calendar_service()
    
    if not service or not calendar_id:
        print("Failed to initialize calendar service")
        return

    try:
        print("Fetching all calendars:")
        calendar_list = service.calendarList().list().execute().get('items', [])
        for calendar in calendar_list:
            print(f"- {calendar['summary']}")

        current_time = get_ist_time()
        event_time = current_time + timedelta(days=1)
        event_details = {
            'summary': 'Python Meeting',
            'location': 'Chennai, Tamil Nadu, India',
            'description': 'A meeting to discuss Python projects.',
            'start': {
                'dateTime': event_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': (event_time + timedelta(hours=1)).isoformat(),
                'timeZone': TIMEZONE,
            },
        }
        
        created_event = create_event(service, calendar_id, event_details)
        
        if created_event:
            print("\nSearching for events:")
            
            print("\nSearching by name 'Python':")
            events_by_name = get_events(service, calendar_id, event_name='Python')
            for event in events_by_name:
                print(f"- {event['summary']} at {event['start'].get('dateTime', 'No time')}")
            
            print("\nSearching by date range:")
            start_date = current_time
            end_date = current_time + timedelta(days=2)
            events_by_date = get_events(
                service, 
                calendar_id, 
                start_date=start_date,
                end_date=end_date
            )
            for event in events_by_date:
                print(f"- {event['summary']} at {event['start'].get('dateTime', 'No time')}")
            
            print("\nSearching by both name and date:")
            events_by_both = get_events(
                service,
                calendar_id,
                event_name='Python',
                start_date=start_date,
                end_date=end_date
            )
            for event in events_by_both:
                print(f"- {event['summary']} at {event['start'].get('dateTime', 'No time')}")
            
            updated_details = {
                'summary': 'An updated meeting to discuss Python projects.',
                'location': 'Chennai, Tamil Nadu, India',
                'description': 'An updated meeting to discuss Python projects.',
                'start': {
                    'dateTime': event_time.isoformat(),
                    'timeZone': TIMEZONE,
                },
                'end': {
                    'dateTime': (event_time + timedelta(hours=1)).isoformat(),
                    'timeZone': TIMEZONE,
                },
            }
            updated_event = update_event(
                service, 
                calendar_id, 
                updated_details,
                event_name='Python Meeting'
            )
            
            if updated_event:
                delete_event(
                    service, 
                    calendar_id, 
                    event_date=event_time
                )

    except Exception as e:
        print(f"Error in main execution: {str(e)}")

if __name__ == '__main__':
    main()