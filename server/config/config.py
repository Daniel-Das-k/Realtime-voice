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
Configuration for Vertex AI Gemini Multimodal Live Proxy Server
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('PROJECT_ID')
    
    if not project_id:
        raise ConfigurationError("PROJECT_ID environment variable is not set")
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        raise


class ApiConfig:
    """API configuration handler."""
    
    def __init__(self):
        # Determine if using Vertex AI
        self.use_vertex = os.getenv('VERTEX_API', 'false').lower() == 'true'
        
        self.api_key: Optional[str] = None
        
        logger.info(f"Initialized API configuration with Vertex AI: {self.use_vertex}")
    
    async def initialize(self):
        """Initialize API credentials."""
        try:
            # Always try to get OpenWeather API key regardless of endpoint
            self.weather_api_key = get_secret('OPENWEATHER_API_KEY')
        except Exception as e:
            logger.warning(f"Failed to get OpenWeather API key from Secret Manager: {e}")
            self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
            if not self.weather_api_key:
                raise ConfigurationError("OpenWeather API key not available")

        if not self.use_vertex:
            try:
                self.api_key = get_secret('GOOGLE_API_KEY')
            except Exception as e:
                logger.warning(f"Failed to get API key from Secret Manager: {e}")
                self.api_key = os.getenv('GOOGLE_API_KEY')
                if not self.api_key:
                    raise ConfigurationError("No API key available from Secret Manager or environment")

# Initialize API configuration
api_config = ApiConfig()

# Model configuration
if api_config.use_vertex:
    MODEL = os.getenv('MODEL_VERTEX_API', 'gemini-2.0-flash-exp')
    VOICE = os.getenv('VOICE_VERTEX_API', 'Aoede')
else:
    MODEL = os.getenv('MODEL_DEV_API', 'models/gemini-2.0-flash-exp')
    VOICE = os.getenv('VOICE_DEV_API', 'Puck')

# Cloud Function URLs with validation
CLOUD_FUNCTIONS = {
    "get_weather": os.getenv('WEATHER_FUNCTION_URL'),
    "get_weather_forecast": os.getenv('FORECAST_FUNCTION_URL'),
    "get_next_appointment": os.getenv('CALENDAR_FUNCTION_URL'),
    "get_past_appointments": os.getenv('PAST_APPOINTMENTS_FUNCTION_URL'),
}

# Validate Cloud Function URLs
for name, url in CLOUD_FUNCTIONS.items():
    if not url:
        logger.warning(f"Missing URL for cloud function: {name}")
    elif not url.startswith('https://'):
        logger.warning(f"Invalid URL format for {name}: {url}")

# Load system instructions
try:
    with open('config/system-instructions.txt', 'r') as f:
        SYSTEM_INSTRUCTIONS = f.read()
except Exception as e:
    logger.error(f"Failed to load system instructions: {e}")
    SYSTEM_INSTRUCTIONS = ""

logger.info(f"System instructions: {SYSTEM_INSTRUCTIONS}")

# Gemini Configuration
CONFIG = {
    "generation_config": {
        "response_modalities": ["AUDIO"],
        "speech_config": VOICE
    },
    "tools": [{
        "function_declarations": [
            {
                "name": "get_weather",
                "description": "Get weather information for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city or location to get weather for"
                        }
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_date_and_time",
                "description": "Get current date and time information for a specific timezone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone to get date and time for (e.g., 'America/New_York', 'asia/kolkata', 'Asia/Tokyo'). If not provided, defaults to asia/kolkata."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "create_event",
                "description": "Create a new calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Title or summary of the event"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location of the event"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the event"
                        },
                        "start": {
                            "type": "object",
                            "properties": {
                                "dateTime": {
                                    "type": "string",
                                    "description": "Start time of the event in ISO format"
                                },
                                "timeZone": {
                                    "type": "string",
                                    "description": "Timezone of the event (defaults to Asia/Kolkata)"
                                }
                            },
                            "required": ["dateTime"]
                        },
                        "end": {
                            "type": "object",
                            "properties": {
                                "dateTime": {
                                    "type": "string",
                                    "description": "End time of the event in ISO format"
                                },
                                "timeZone": {
                                    "type": "string",
                                    "description": "Timezone of the event (defaults to Asia/Kolkata)"
                                }
                            },
                            "required": ["dateTime"]
                        }
                    },
                    "required": ["summary", "start", "end"]
                }
            },
            {
                "name": "update_event",
                "description": "Update an existing calendar event by name or date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_name": {
                            "type": "string",
                            "description": "Name of the event to update (optional if event_date is provided)"
                        },
                        "event_date": {
                            "type": "string",
                            "description": "Date and time of the event to update in ISO format (optional if event_name is provided)"
                        },
                        "updated_details": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "New title or summary of the event"
                                },
                                "location": {
                                    "type": "string",
                                    "description": "New location of the event"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "New detailed description of the event"
                                },
                                "start": {
                                    "type": "object",
                                    "properties": {
                                        "dateTime": {
                                            "type": "string",
                                            "description": "New start time of the event in ISO format"
                                        },
                                        "timeZone": {
                                            "type": "string",
                                            "description": "Timezone of the event (defaults to Asia/Kolkata)"
                                        }
                                    }
                                },
                                "end": {
                                    "type": "object",
                                    "properties": {
                                        "dateTime": {
                                            "type": "string",
                                            "description": "New end time of the event in ISO format"
                                        },
                                        "timeZone": {
                                            "type": "string",
                                            "description": "Timezone of the event (defaults to Asia/Kolkata)"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["updated_details"],
                    "oneOf": [
                        {"required": ["event_name"]},
                        {"required": ["event_date"]}
                    ]
                }
            },
            {
                "name": "delete_event",
                "description": "Delete a calendar event by name or date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_name": {
                            "type": "string",
                            "description": "Name of the event to delete (optional if event_date is provided)"
                        },
                        "event_date": {
                            "type": "string",
                            "description": "Date and time of the event to delete in ISO format (optional if event_name is provided)"
                        }
                    },
                    "oneOf": [
                        {"required": ["event_name"]},
                        {"required": ["event_date"]}
                    ]
                }
            },
            {
                "name": "get_events",
                "description": "Search for calendar events by name and/or date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_name": {
                            "type": "string",
                            "description": "Name or keyword to search for in event summaries"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date for search range in ISO format (defaults to current time)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for search range in ISO format (defaults to start_date + 30 days)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_all_events",
                "description": "Get all events from the calendar within a one-year range",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "add_note",
                "description": "Add a new note or update an existing one",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_name": {
                            "type": "string",
                            "description": "Name of the note (required)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content of the note (required)"
                        }
                    },
                    "required": ["note_name", "content"]
                }
            },
            {
                "name": "get_note",
                "description": "Get a specific note by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_name": {
                            "type": "string",
                            "description": "Name of the note to retrieve"
                        }
                    },
                    "required": ["note_name"]
                }
            },
            {
                "name": "get_all_notes",
                "description": "Get all notes from the system",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "delete_note",
                "description": "Delete a note by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_name": {
                            "type": "string",
                            "description": "Name of the note to delete"
                        }
                    },
                    "required": ["note_name"]
                }
            }
        ]
    }],
    "system_instruction": SYSTEM_INSTRUCTIONS
} 