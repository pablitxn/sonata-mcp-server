from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from config.logger import get_logger
from connectors.atc_sports.connector import ATCSportsConnector
from connectors.atc_sports.interfaces import DateRange, TimeRange
from telemetry.context import trace

logger = get_logger(__name__)

atc_connector: Optional[ATCSportsConnector] = None


async def get_or_create_connector() -> ATCSportsConnector:
    global atc_connector
    if atc_connector is None:
        atc_connector = ATCSportsConnector()
    return atc_connector


ATC_SPORTS_TOOLS = [
    Tool(
        name="atc_sports_login_request",
        description="Start ATC Sports booking process by requesting magic link email",
        inputSchema={
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address to send magic link to"
                }
            },
            "required": ["email"]
        }
    ),
    Tool(
        name="atc_sports_login_with_url",
        description="Complete ATC Sports login using magic link from email",
        inputSchema={
            "type": "object",
            "properties": {
                "magic_link_url": {
                    "type": "string",
                    "description": "The magic link URL received in email"
                }
            },
            "required": ["magic_link_url"]
        }
    ),
    Tool(
        name="atc_sports_refresh_session",
        description="Refresh ATC Sports session to prevent timeout",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="atc_sports_logout",
        description="Logout from ATC Sports and clear session",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="atc_sports_get_session_status",
        description="Check if ATC Sports session is still valid",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="atc_sports_add_favorite_court",
        description="Add a court to favorites for quick access",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Court name"
                },
                "location": {
                    "type": "string",
                    "description": "Court location (address or neighborhood)"
                },
                "court_type": {
                    "type": "string",
                    "description": "Type of court",
                    "enum": ["futbol5", "futbol7", "tennis", "paddle"]
                },
                "preferred_days": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                    },
                    "description": "Preferred days to play"
                },
                "preferred_time": {
                    "type": "string",
                    "description": "Preferred time of day",
                    "enum": ["morning", "afternoon", "evening", "night"]
                }
            },
            "required": ["name", "location", "court_type", "preferred_days"]
        }
    ),
    Tool(
        name="atc_sports_view_favorite_courts",
        description="View all saved favorite courts",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="atc_sports_edit_favorite_court",
        description="Update details of a favorite court",
        inputSchema={
            "type": "object",
            "properties": {
                "court_id": {
                    "type": "string",
                    "description": "ID of the favorite court to edit"
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update",
                    "properties": {
                        "preferred_days": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "preferred_time": {"type": "string"}
                    }
                }
            },
            "required": ["court_id", "updates"]
        }
    ),
    Tool(
        name="atc_sports_remove_favorite_court",
        description="Remove a court from favorites",
        inputSchema={
            "type": "object",
            "properties": {
                "court_id": {
                    "type": "string",
                    "description": "ID of the favorite court to remove"
                }
            },
            "required": ["court_id"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_neighborhood",
        description="Find available courts in a specific neighborhood",
        inputSchema={
            "type": "object",
            "properties": {
                "neighborhood": {
                    "type": "string",
                    "description": "Neighborhood name (e.g., Palermo, Recoleta)"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "from_time": {
                            "type": "string",
                            "description": "Start time in HH:MM format"
                        },
                        "to_time": {
                            "type": "string",
                            "description": "End time in HH:MM format"
                        }
                    }
                },
                "court_type": {
                    "type": "string",
                    "enum": ["futbol5", "futbol7", "tennis", "paddle"]
                }
            },
            "required": ["neighborhood", "date"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_date",
        description="Find all available courts for a specific date",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Specific time in HH:MM format"
                },
                "court_type": {
                    "type": "string",
                    "enum": ["futbol5", "futbol7", "tennis", "paddle"]
                }
            },
            "required": ["date"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_favorites",
        description="Check availability of favorite courts within date range",
        inputSchema={
            "type": "object",
            "properties": {
                "date_range": {
                    "type": "object",
                    "properties": {
                        "from_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "to_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["from_date", "to_date"]
                },
                "time_preference": {
                    "type": "string",
                    "enum": ["morning", "afternoon", "evening", "night"]
                }
            },
            "required": ["date_range"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_type",
        description="Find available courts of specific type",
        inputSchema={
            "type": "object",
            "properties": {
                "court_type": {
                    "type": "string",
                    "enum": ["futbol5", "futbol7", "tennis", "paddle"]
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "neighborhood": {
                    "type": "string",
                    "description": "Optional neighborhood filter"
                }
            },
            "required": ["court_type", "date"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_max_price",
        description="Find courts within budget",
        inputSchema={
            "type": "object",
            "properties": {
                "max_price": {
                    "type": "number",
                    "description": "Maximum price per hour"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Specific time in HH:MM format"
                }
            },
            "required": ["max_price", "date"]
        }
    ),
    Tool(
        name="atc_sports_check_availability_by_time",
        description="Find courts available at specific time across multiple dates",
        inputSchema={
            "type": "object",
            "properties": {
                "time_slot": {
                    "type": "string",
                    "description": "Time slot in HH:MM format"
                },
                "date_range": {
                    "type": "object",
                    "properties": {
                        "from_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "to_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["from_date", "to_date"]
                },
                "court_type": {
                    "type": "string",
                    "enum": ["futbol5", "futbol7", "tennis", "paddle"]
                }
            },
            "required": ["time_slot", "date_range"]
        }
    ),
    Tool(
        name="atc_sports_search_courts_near",
        description="Find courts near a location",
        inputSchema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Address to search near"
                },
                "coordinates": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"}
                    }
                },
                "radius_km": {
                    "type": "number",
                    "description": "Search radius in kilometers",
                    "default": 5.0
                }
            }
        }
    ),
    Tool(
        name="atc_sports_book_court_by_id",
        description="Book a specific court",
        inputSchema={
            "type": "object",
            "properties": {
                "court_id": {
                    "type": "string",
                    "description": "ID of the court to book"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Time slot in HH:MM format"
                },
                "duration_hours": {
                    "type": "number",
                    "description": "Duration in hours (usually 1 or 2)"
                },
                "player_count": {
                    "type": "number",
                    "description": "Number of players"
                }
            },
            "required": ["court_id", "date", "time_slot", "duration_hours"]
        }
    ),
    Tool(
        name="atc_sports_cancel_booking",
        description="Cancel an existing booking",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "ID of the booking to cancel"
                },
                "reason": {
                    "type": "string",
                    "description": "Optional cancellation reason"
                }
            },
            "required": ["booking_id"]
        }
    ),
    Tool(
        name="atc_sports_view_active_bookings",
        description="View all future bookings",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="atc_sports_view_booking_history",
        description="View past bookings history",
        inputSchema={
            "type": "object",
            "properties": {
                "from_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "to_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results"
                }
            }
        }
    ),
    Tool(
        name="atc_sports_view_booking_details",
        description="Get detailed information about a specific booking",
        inputSchema={
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "ID of the booking"
                }
            },
            "required": ["booking_id"]
        }
    )
]


@trace("atc_sports_tools.execute")
async def execute_atc_sports_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    logger.info(f"Executing ATC Sports tool: {tool_name}")
    connector = await get_or_create_connector()
    
    try:
        if tool_name == "atc_sports_login_request":
            result = await connector.login_request(arguments["email"])
            
        elif tool_name == "atc_sports_login_with_url":
            result = await connector.login_with_url(arguments["magic_link_url"])
            
        elif tool_name == "atc_sports_refresh_session":
            result = await connector.refresh_session()
            
        elif tool_name == "atc_sports_logout":
            result = await connector.logout()
            
        elif tool_name == "atc_sports_get_session_status":
            status = await connector.get_session_status()
            result = {
                "is_valid": status.is_valid,
                "expires_in_minutes": status.expires_in_minutes
            }
            
        elif tool_name == "atc_sports_add_favorite_court":
            favorite = await connector.add_favorite_court(
                arguments["name"],
                arguments["location"],
                arguments["court_type"],
                arguments["preferred_days"],
                arguments.get("preferred_time")
            )
            result = {
                "id": favorite.id,
                "name": favorite.name,
                "location": favorite.location,
                "court_type": favorite.court_type,
                "preferred_days": favorite.preferred_days,
                "preferred_time": favorite.preferred_time
            }
            
        elif tool_name == "atc_sports_view_favorite_courts":
            favorites = await connector.view_favorite_courts()
            result = [
                {
                    "id": f.id,
                    "name": f.name,
                    "location": f.location,
                    "court_type": f.court_type,
                    "preferred_days": f.preferred_days,
                    "preferred_time": f.preferred_time
                }
                for f in favorites
            ]
            
        elif tool_name == "atc_sports_edit_favorite_court":
            favorite = await connector.edit_favorite_court(
                arguments["court_id"],
                arguments["updates"]
            )
            result = {
                "id": favorite.id,
                "name": favorite.name,
                "location": favorite.location,
                "court_type": favorite.court_type,
                "preferred_days": favorite.preferred_days,
                "preferred_time": favorite.preferred_time
            }
            
        elif tool_name == "atc_sports_remove_favorite_court":
            result = await connector.remove_favorite_court(arguments["court_id"])
            
        elif tool_name == "atc_sports_check_availability_by_neighborhood":
            time_range = None
            if "time_range" in arguments:
                time_range = TimeRange(
                    from_time=arguments["time_range"]["from_time"],
                    to_time=arguments["time_range"]["to_time"]
                )
            
            availabilities = await connector.check_availability_by_neighborhood(
                arguments["neighborhood"],
                arguments["date"],
                time_range,
                arguments.get("court_type")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_check_availability_by_date":
            availabilities = await connector.check_availability_by_date(
                arguments["date"],
                arguments.get("time_slot"),
                arguments.get("court_type")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_check_availability_by_favorites":
            date_range = DateRange(
                from_date=arguments["date_range"]["from_date"],
                to_date=arguments["date_range"]["to_date"]
            )
            availabilities = await connector.check_availability_by_favorites(
                date_range,
                arguments.get("time_preference")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_check_availability_by_type":
            availabilities = await connector.check_availability_by_type(
                arguments["court_type"],
                arguments["date"],
                arguments.get("neighborhood")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_check_availability_by_max_price":
            availabilities = await connector.check_availability_by_max_price(
                arguments["max_price"],
                arguments["date"],
                arguments.get("time_slot")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_check_availability_by_time":
            date_range = DateRange(
                from_date=arguments["date_range"]["from_date"],
                to_date=arguments["date_range"]["to_date"]
            )
            availabilities = await connector.check_availability_by_time(
                arguments["time_slot"],
                date_range,
                arguments.get("court_type")
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_search_courts_near":
            from connectors.atc_sports.interfaces import Coordinates
            
            coordinates = None
            if "coordinates" in arguments:
                coordinates = Coordinates(
                    lat=arguments["coordinates"]["lat"],
                    lng=arguments["coordinates"]["lng"]
                )
            
            availabilities = await connector.search_courts_near(
                arguments.get("address"),
                coordinates,
                arguments.get("radius_km", 5.0)
            )
            result = [
                {
                    "court_id": a.court_id,
                    "court_name": a.court_name,
                    "location": a.location,
                    "court_type": a.court_type,
                    "date": a.date,
                    "time_slots": a.time_slots,
                    "price_per_hour": a.price_per_hour,
                    "address": a.address,
                    "neighborhood": a.neighborhood
                }
                for a in availabilities
            ]
            
        elif tool_name == "atc_sports_book_court_by_id":
            booking = await connector.book_court_by_id(
                arguments["court_id"],
                arguments["date"],
                arguments["time_slot"],
                arguments["duration_hours"],
                arguments.get("player_count")
            )
            result = {
                "booking_id": booking.booking_id,
                "court_id": booking.court_id,
                "court_name": booking.court_name,
                "location": booking.location,
                "date": booking.date,
                "time_slot": booking.time_slot,
                "duration_hours": booking.duration_hours,
                "total_price": booking.total_price,
                "player_count": booking.player_count,
                "confirmation_code": booking.confirmation_code,
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            
        elif tool_name == "atc_sports_cancel_booking":
            result = await connector.cancel_booking(
                arguments["booking_id"],
                arguments.get("reason")
            )
            
        elif tool_name == "atc_sports_view_active_bookings":
            bookings = await connector.view_active_bookings()
            result = [
                {
                    "booking_id": b.booking_id,
                    "court_id": b.court_id,
                    "court_name": b.court_name,
                    "location": b.location,
                    "date": b.date,
                    "time_slot": b.time_slot,
                    "duration_hours": b.duration_hours,
                    "total_price": b.total_price,
                    "player_count": b.player_count,
                    "confirmation_code": b.confirmation_code,
                    "status": b.status
                }
                for b in bookings
            ]
            
        elif tool_name == "atc_sports_view_booking_history":
            bookings = await connector.view_booking_history(
                arguments.get("from_date"),
                arguments.get("to_date"),
                arguments.get("limit")
            )
            result = [
                {
                    "booking_id": b.booking_id,
                    "court_id": b.court_id,
                    "court_name": b.court_name,
                    "location": b.location,
                    "date": b.date,
                    "time_slot": b.time_slot,
                    "duration_hours": b.duration_hours,
                    "total_price": b.total_price,
                    "player_count": b.player_count,
                    "confirmation_code": b.confirmation_code,
                    "status": b.status
                }
                for b in bookings
            ]
            
        elif tool_name == "atc_sports_view_booking_details":
            booking = await connector.view_booking_details(arguments["booking_id"])
            result = {
                "booking_id": booking.booking_id,
                "court_id": booking.court_id,
                "court_name": booking.court_name,
                "location": booking.location,
                "date": booking.date,
                "time_slot": booking.time_slot,
                "duration_hours": booking.duration_hours,
                "total_price": booking.total_price,
                "player_count": booking.player_count,
                "confirmation_code": booking.confirmation_code,
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        logger.info(f"ATC Sports tool {tool_name} executed successfully")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error executing ATC Sports tool {tool_name}: {e}")
        return json.dumps({
            "error": str(e),
            "tool": tool_name
        })