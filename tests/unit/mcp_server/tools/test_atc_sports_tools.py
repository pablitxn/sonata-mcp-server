import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.mcp_server.tools.atc_sports_tools import (
    ATC_SPORTS_TOOLS,
    execute_atc_sports_tool,
)
from src.connectors.atc_sports.interfaces import (
    SessionStatus,
    FavoriteCourt,
    CourtAvailability,
    Booking,
)


class TestATCSportsTools:
    def test_all_tools_defined(self):
        expected_tools = [
            "atc_sports_login_request",
            "atc_sports_login_with_url",
            "atc_sports_refresh_session",
            "atc_sports_logout",
            "atc_sports_get_session_status",
            "atc_sports_add_favorite_court",
            "atc_sports_view_favorite_courts",
            "atc_sports_edit_favorite_court",
            "atc_sports_remove_favorite_court",
            "atc_sports_check_availability_by_neighborhood",
            "atc_sports_check_availability_by_date",
            "atc_sports_check_availability_by_favorites",
            "atc_sports_check_availability_by_type",
            "atc_sports_check_availability_by_max_price",
            "atc_sports_check_availability_by_time",
            "atc_sports_search_courts_near",
            "atc_sports_book_court_by_id",
            "atc_sports_cancel_booking",
            "atc_sports_view_active_bookings",
            "atc_sports_view_booking_history",
            "atc_sports_view_booking_details",
        ]
        
        tool_names = [tool.name for tool in ATC_SPORTS_TOOLS]
        assert set(tool_names) == set(expected_tools)

    @pytest.mark.asyncio
    async def test_execute_login_request(self):
        mock_connector = Mock()
        mock_connector.login_request = AsyncMock(return_value={
            "status": "success",
            "message": "Magic link sent",
            "email": "test@example.com"
        })
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_login_request", {"email": "test@example.com"})
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["email"] == "test@example.com"
            mock_connector.login_request.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_execute_get_session_status(self):
        mock_connector = Mock()
        mock_status = SessionStatus(is_valid=True, expires_in_minutes=45)
        mock_connector.get_session_status = AsyncMock(return_value=mock_status)
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_get_session_status", {})
            
            result_data = json.loads(result)
            assert result_data["is_valid"] is True
            assert result_data["expires_in_minutes"] == 45

    @pytest.mark.asyncio
    async def test_execute_add_favorite_court(self):
        mock_connector = Mock()
        mock_favorite = FavoriteCourt(
            id="123",
            name="Test Court",
            location="Test Location",
            court_type="futbol5",
            preferred_days=["mon", "wed"],
            preferred_time="evening"
        )
        mock_connector.add_favorite_court = AsyncMock(return_value=mock_favorite)
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_add_favorite_court", {
                "name": "Test Court",
                "location": "Test Location",
                "court_type": "futbol5",
                "preferred_days": ["mon", "wed"],
                "preferred_time": "evening"
            })
            
            result_data = json.loads(result)
            assert result_data["id"] == "123"
            assert result_data["name"] == "Test Court"
            assert result_data["preferred_days"] == ["mon", "wed"]

    @pytest.mark.asyncio
    async def test_execute_check_availability_by_neighborhood(self):
        mock_connector = Mock()
        mock_availability = CourtAvailability(
            court_id="1",
            court_name="Court 1",
            location="Location 1",
            court_type="futbol5",
            date="2024-01-20",
            time_slots=["19:00", "20:00"],
            price_per_hour=5000.0,
            address="Address 1",
            neighborhood="Palermo"
        )
        mock_connector.check_availability_by_neighborhood = AsyncMock(return_value=[mock_availability])
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_check_availability_by_neighborhood", {
                "neighborhood": "Palermo",
                "date": "2024-01-20",
                "time_range": {
                    "from_time": "18:00",
                    "to_time": "22:00"
                }
            })
            
            result_data = json.loads(result)
            assert len(result_data) == 1
            assert result_data[0]["court_name"] == "Court 1"
            assert result_data[0]["neighborhood"] == "Palermo"

    @pytest.mark.asyncio
    async def test_execute_book_court_by_id(self):
        mock_connector = Mock()
        mock_booking = Booking(
            booking_id="booking123",
            court_id="1",
            court_name="Court 1",
            location="Location 1",
            date="2024-01-20",
            time_slot="19:00",
            duration_hours=2,
            total_price=10000.0,
            player_count=10,
            confirmation_code="CONF123",
            status="active"
        )
        mock_connector.book_court_by_id = AsyncMock(return_value=mock_booking)
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_book_court_by_id", {
                "court_id": "1",
                "date": "2024-01-20",
                "time_slot": "19:00",
                "duration_hours": 2,
                "player_count": 10
            })
            
            result_data = json.loads(result)
            assert result_data["booking_id"] == "booking123"
            assert result_data["confirmation_code"] == "CONF123"
            assert result_data["total_price"] == 10000.0

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector'):
            result = await execute_atc_sports_tool("unknown_tool", {})
            
            result_data = json.loads(result)
            assert "error" in result_data
            assert "Unknown tool" in result_data["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self):
        mock_connector = Mock()
        mock_connector.login_request = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('src.mcp_server.tools.atc_sports_tools.get_or_create_connector', return_value=mock_connector):
            result = await execute_atc_sports_tool("atc_sports_login_request", {"email": "test@example.com"})
            
            result_data = json.loads(result)
            assert "error" in result_data
            assert "Connection failed" in result_data["error"]

    def test_tool_input_schemas(self):
        for tool in ATC_SPORTS_TOOLS:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert tool.inputSchema['type'] == 'object'
            assert 'properties' in tool.inputSchema