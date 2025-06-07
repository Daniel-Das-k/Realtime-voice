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
from typing import Dict, Any
from config.config import CLOUD_FUNCTIONS
from urllib.parse import urlencode
import sys
from weather import get_weather

# Python 3.9+ has zoneinfo in the standard library
if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    ZoneInfo = None  # Fallback if needed

logger = logging.getLogger(__name__)

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on name and parameters by calling the corresponding cloud function or locally for date/time."""
    try:
        if tool_name == "get_date_and_time":
            # Local date and time logic
            timezone = params.get("timezone", "Asia/Kolkata")
            try:
                if ZoneInfo is not None:
                    tz = ZoneInfo(timezone)
                else:
                    tz = None  # Fallback to IST if zoneinfo not available
            except Exception:
                tz = None
            now = datetime.datetime.now(tz) if tz else datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
            response = {
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "timezone": timezone if tz else "Asia/Kolkata",
                "timestamp": int(now.timestamp()),
                "day_of_week": now.strftime('%A'),
                "is_dst": bool(now.dst()) if tz else False,
                "utc_offset": str(now.utcoffset()) if tz else "+05:30",
                "formatted": now.strftime('%Y-%m-%d %H:%M:%S %Z')
            }
            return response
        elif tool_name == "get_weather":
            # Local weather logic
            return get_weather(params)
        elif tool_name in CLOUD_FUNCTIONS:
            base_url = CLOUD_FUNCTIONS[tool_name]
            # Convert params to URL query parameters
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
                        return await response.json()
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