# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tool execution and handling for Gemini Multimodal Live Proxy Server
"""

import logging
import datetime
import aiohttp
from typing import Dict, Any, Optional
from config.config import CLOUD_FUNCTIONS
from urllib.parse import urlencode
import sys
from weather import get_weather
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from note_taking import NoteTaking

# Python 3.9+ has zoneinfo in the standard library
if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    ZoneInfo = None  # Fallback if needed

logger = logging.getLogger(__name__)

# Supported languages configuration
SUPPORTED_LANGUAGES = {
    # English
    'en': {
        'name': 'English',
        'weather_api_code': 'en',
        'timezone': 'Asia/Kolkata'
    },
    # Indian Languages
    'ta': {
        'name': 'Tamil',
        'weather_api_code': 'ta',
        'timezone': 'Asia/Kolkata'
    },
    'hi': {
        'name': 'Hindi',
        'weather_api_code': 'hi',
        'timezone': 'Asia/Kolkata'
    },
    'te': {
        'name': 'Telugu',
        'weather_api_code': 'te',
        'timezone': 'Asia/Kolkata'
    },
    'ml': {
        'name': 'Malayalam',
        'weather_api_code': 'ml',
        'timezone': 'Asia/Kolkata'
    },
    'kn': {
        'name': 'Kannada',
        'weather_api_code': 'kn',
        'timezone': 'Asia/Kolkata'
    },
    'bn': {
        'name': 'Bengali',
        'weather_api_code': 'bn',
        'timezone': 'Asia/Kolkata'
    },
    'mr': {
        'name': 'Marathi',
        'weather_api_code': 'mr',
        'timezone': 'Asia/Kolkata'
    },
    'gu': {
        'name': 'Gujarati',
        'weather_api_code': 'gu',
        'timezone': 'Asia/Kolkata'
    },
    'pa': {
        'name': 'Punjabi',
        'weather_api_code': 'pa',
        'timezone': 'Asia/Kolkata'
    },
    'or': {
        'name': 'Odia',
        'weather_api_code': 'or',
        'timezone': 'Asia/Kolkata'
    },
    # Other Asian Languages
    'zh': {
        'name': 'Chinese',
        'weather_api_code': 'zh_cn',
        'timezone': 'Asia/Shanghai'
    },
    'ja': {
        'name': 'Japanese',
        'weather_api_code': 'ja',
        'timezone': 'Asia/Tokyo'
    },
    'ko': {
        'name': 'Korean',
        'weather_api_code': 'kr',
        'timezone': 'Asia/Seoul'
    },
    # European Languages
    'fr': {
        'name': 'French',
        'weather_api_code': 'fr',
        'timezone': 'Europe/Paris'
    },
    'de': {
        'name': 'German',
        'weather_api_code': 'de',
        'timezone': 'Europe/Berlin'
    },
    'es': {
        'name': 'Spanish',
        'weather_api_code': 'es',
        'timezone': 'Europe/Madrid'
    },
    'it': {
        'name': 'Italian',
        'weather_api_code': 'it',
        'timezone': 'Europe/Rome'
    },
    'pt': {
        'name': 'Portuguese',
        'weather_api_code': 'pt',
        'timezone': 'Europe/Lisbon'
    },
    'ru': {
        'name': 'Russian',
        'weather_api_code': 'ru',
        'timezone': 'Europe/Moscow'
    },
    # Middle Eastern Languages
    'ar': {
        'name': 'Arabic',
        'weather_api_code': 'ar',
        'timezone': 'Asia/Riyadh'
    },
    'fa': {
        'name': 'Persian',
        'weather_api_code': 'fa',
        'timezone': 'Asia/Tehran'
    },
    'tr': {
        'name': 'Turkish',
        'weather_api_code': 'tr',
        'timezone': 'Europe/Istanbul'
    }
}

def detect_language(text: str) -> str:
    """
    Detect the language of the input text.
    Returns the language code if supported, otherwise returns 'en'.
    """
    if not text or not isinstance(text, str):
        return 'en'
        
    try:
        # Set seed for consistent results
        DetectorFactory.seed = 0
        # Detect language
        lang_code = detect(text)
        # Return detected language if supported, otherwise default to English
        return lang_code if lang_code in SUPPORTED_LANGUAGES else 'en'
    except LangDetectException:
        logger.warning("Could not detect language, defaulting to English")
        return 'en'

def get_language_config(lang_code: str) -> Dict[str, str]:
    """
    Get the configuration for a specific language.
    Returns English configuration if language is not supported.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES['en'])

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on name and parameters by calling the corresponding cloud function or locally for date/time."""
    try:
        # Detect language from user query if present
        user_query = params.get('query', '')
        detected_lang = detect_language(user_query)
        lang_config = get_language_config(detected_lang)
        
        # Log language detection
        logger.info(f"Detected language: {lang_config['name']}")
        
        # Initialize note taking system
        note_taker = NoteTaking()
        
        # Handle note-taking operations
        if tool_name == "add_note":
            try:
                result = note_taker.add_note(
                    note_name=params.get('note_name'),
                    content=params.get('content')
                )
                # Add language information to response
                if isinstance(result, dict):
                    result['language'] = {
                        "code": detected_lang,
                        "name": lang_config['name']
                    }
                return result
            except Exception as e:
                logger.error(f"Note creation/update failed: {str(e)}")
                return {"error": f"Note operation failed: {str(e)}"}
                
        elif tool_name == "get_note":
            try:
                result = note_taker.get_note(params.get('note_name'))
                # Add language information to response
                if isinstance(result, dict):
                    result['language'] = {
                        "code": detected_lang,
                        "name": lang_config['name']
                    }
                return result
            except Exception as e:
                logger.error(f"Note retrieval failed: {str(e)}")
                return {"error": f"Note retrieval failed: {str(e)}"}
                
        elif tool_name == "get_all_notes":
            try:
                result = note_taker.get_all_notes()
                # Add language information to response
                if isinstance(result, dict):
                    result['language'] = {
                        "code": detected_lang,
                        "name": lang_config['name']
                    }
                return result
            except Exception as e:
                logger.error(f"Notes retrieval failed: {str(e)}")
                return {"error": f"Notes retrieval failed: {str(e)}"}
                
        elif tool_name == "delete_note":
            try:
                result = note_taker.delete_note(params.get('note_name'))
                # Add language information to response
                if isinstance(result, dict):
                    result['language'] = {
                        "code": detected_lang,
                        "name": lang_config['name']
                    }
                return result
            except Exception as e:
                logger.error(f"Note deletion failed: {str(e)}")
                return {"error": f"Note deletion failed: {str(e)}"}
        
        elif tool_name == "get_date_and_time":
            # Local date and time logic with language-specific timezone
            timezone = params.get("timezone", lang_config['timezone'])
            try:
                if ZoneInfo is not None:
                    tz = ZoneInfo(timezone)
                else:
                    tz = None
            except Exception:
                tz = None
                
            now = datetime.datetime.now(tz) if tz else datetime.datetime.now(ZoneInfo(lang_config['timezone']))
            response = {
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "timezone": timezone if tz else lang_config['timezone'],
                "timestamp": int(now.timestamp()),
                "day_of_week": now.strftime('%A'),
                "is_dst": bool(now.dst()) if tz else False,
                "utc_offset": str(now.utcoffset()) if tz else "+05:30",
                "formatted": now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "language": {
                    "code": detected_lang,
                    "name": lang_config['name']
                }
            }
            return response
            
        elif tool_name == "get_weather":
            # Add language-specific parameters to weather request
            weather_params = params.copy()
            weather_params['lang'] = lang_config['weather_api_code']
            weather_info = get_weather(weather_params)
            
            # Add language information to response
            if isinstance(weather_info, dict):
                weather_info['language'] = {
                    "code": detected_lang,
                    "name": lang_config['name']
                }
            return weather_info
            
        elif tool_name in ["create_event", "update_event", "delete_event", "get_events", "get_all_events"]:
            # Calendar operations
            try:
                from schedule import (
                    get_calendar_service,
                    create_event,
                    update_event,
                    delete_event,
                    get_events,
                    get_all_events
                )
                
                # Get calendar service
                service, calendar_id = get_calendar_service()
                if not service or not calendar_id:
                    return {"error": "Failed to initialize calendar service"}
                
                if tool_name == "create_event":
                    # Ensure timezone is set to language-specific timezone
                    if 'start' in params:
                        params['start']['timeZone'] = lang_config['timezone']
                    if 'end' in params:
                        params['end']['timeZone'] = lang_config['timezone']
                    
                    result = create_event(service, calendar_id, params)
                    
                elif tool_name == "update_event":
                    # Convert string dates to datetime objects if provided
                    event_date = None
                    if 'event_date' in params:
                        try:
                            event_date = datetime.datetime.fromisoformat(params['event_date'])
                        except ValueError:
                            return {"error": "Invalid event_date format. Use ISO format."}
                    
                    # Ensure timezone is set in updated_details
                    updated_details = params.get('updated_details', {})
                    if 'start' in updated_details:
                        updated_details['start']['timeZone'] = lang_config['timezone']
                    if 'end' in updated_details:
                        updated_details['end']['timeZone'] = lang_config['timezone']
                    
                    result = update_event(
                        service,
                        calendar_id,
                        updated_details,
                        event_name=params.get('event_name'),
                        event_date=event_date
                    )
                    
                elif tool_name == "delete_event":
                    # Convert string date to datetime object if provided
                    event_date = None
                    if 'event_date' in params:
                        try:
                            event_date = datetime.datetime.fromisoformat(params['event_date'])
                        except ValueError:
                            return {"error": "Invalid event_date format. Use ISO format."}
                    
                    result = delete_event(
                        service,
                        calendar_id,
                        event_name=params.get('event_name'),
                        event_date=event_date
                    )
                    
                elif tool_name == "get_events":
                    # Convert string dates to datetime objects if provided
                    start_date = None
                    end_date = None
                    if 'start_date' in params:
                        try:
                            start_date = datetime.datetime.fromisoformat(params['start_date'])
                        except ValueError:
                            return {"error": "Invalid start_date format. Use ISO format."}
                    if 'end_date' in params:
                        try:
                            end_date = datetime.datetime.fromisoformat(params['end_date'])
                        except ValueError:
                            return {"error": "Invalid end_date format. Use ISO format."}
                    
                    result = get_events(
                        service,
                        calendar_id,
                        event_name=params.get('event_name'),
                        start_date=start_date,
                        end_date=end_date
                    )
                
                elif tool_name == "get_all_events":
                    result = get_all_events(service, calendar_id)
                
                # Add language information to response
                if isinstance(result, dict):
                    result['language'] = {
                        "code": detected_lang,
                        "name": lang_config['name']
                    }
                elif isinstance(result, list):
                    result = {
                        "events": result,
                        "language": {
                            "code": detected_lang,
                            "name": lang_config['name']
                        }
                    }
                
                return result
                
            except ImportError:
                logger.error("Failed to import calendar functions")
                return {"error": "Calendar functionality not available"}
            except Exception as e:
                logger.error(f"Calendar operation failed: {str(e)}")
                return {"error": f"Calendar operation failed: {str(e)}"}
            
        elif tool_name in CLOUD_FUNCTIONS:
            base_url = CLOUD_FUNCTIONS[tool_name]
            # Add language information to cloud function parameters
            params['language'] = detected_lang
            params['language_config'] = lang_config
            
            query_string = urlencode(params)
            function_url = f"{base_url}?{query_string}" if params else base_url
            
            logger.debug(f"Calling cloud function for {tool_name}")
            logger.debug(f"URL with params: {function_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(function_url) as response:
                    response_text = await response.text()
                    logger.debug(f"Response status: {response.status}")
                    logger.debug(f"Response headers: {dict(response.headers)}")
                    logger.debug(f"Response body: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Cloud function error: {response_text}")
                        return {"error": f"Cloud function returned status {response.status}"}
                        
                    try:
                        result = await response.json()
                        # Add language information to response
                        if isinstance(result, dict):
                            result['language'] = {
                                "code": detected_lang,
                                "name": lang_config['name']
                            }
                        return result
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {response_text}")
                        return {"error": f"Invalid JSON response from cloud function: {str(e)}"}
        else:
            logger.error(f"Tool not found: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
            
    except aiohttp.ClientError as e:
        logger.error(f"Network error calling cloud function for {tool_name}: {str(e)}")
        return {"error": f"Failed to call cloud function: {str(e)}"}
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        return {"error": f"Tool execution failed: {str(e)}"} 