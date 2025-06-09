import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.connectors.atc_sports.connector import ATCSportsConnector
from src.connectors.atc_sports.interfaces import (
    SessionStatus,
    FavoriteCourt,
    CourtAvailability,
    Booking,
    TimeRange,
    DateRange,
    Coordinates,
)


class TestATCSportsConnector:
    @pytest.fixture
    def connector(self):
        return ATCSportsConnector()

    @pytest.mark.asyncio
    async def test_login_request_success(self, connector):
        email = "test@example.com"
        mock_page = Mock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        
        with patch.object(connector, '_get_page', new_callable=AsyncMock, return_value=mock_page):
            result = await connector.login_request(email)
            
            assert result["status"] == "success"
            assert result["email"] == email
            assert connector.current_email == email
            mock_page.goto.assert_called_once_with("https://atcsports.com/login")

    @pytest.mark.asyncio
    async def test_login_request_failure(self, connector, mock_browser):
        email = "test@example.com"
        mock_browser.find_element.side_effect = Exception("Element not found")
        
        result = await connector.login_request(email)
        
        assert result["status"] == "error"
        assert "Element not found" in result["message"]

    @pytest.mark.asyncio
    async def test_login_with_url_success(self, connector, mock_browser):
        magic_link = "https://atcsports.com/login?token=abc123"
        connector.current_email = "test@example.com"
        mock_browser.execute_script.return_value = "session_token_123"
        
        with patch.object(connector.session_storage, 'save_session_token') as mock_save:
            result = await connector.login_with_url(magic_link)
            
            assert result["status"] == "success"
            assert result["session_valid"] is True
            mock_save.assert_called_once()
            mock_browser.navigate.assert_called_once_with(magic_link)

    @pytest.mark.asyncio
    async def test_refresh_session_success(self, connector, mock_browser):
        connector.current_email = "test@example.com"
        mock_browser.execute_script.return_value = "new_token_123"
        
        with patch.object(connector.session_storage, 'get_session_token', return_value="old_token"):
            with patch.object(connector.session_storage, 'refresh_session') as mock_refresh:
                result = await connector.refresh_session()
                
                assert result["status"] == "success"
                mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout(self, connector, mock_browser):
        connector.current_email = "test@example.com"
        
        with patch.object(connector.session_storage, 'clear_session') as mock_clear:
            result = await connector.logout()
            
            assert result["status"] == "success"
            assert connector.current_email is None
            mock_clear.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_get_session_status_valid(self, connector):
        connector.current_email = "test@example.com"
        
        with patch.object(connector.session_storage, 'is_session_valid', return_value=True):
            with patch.object(connector.session_storage, 'get_session_expires_in_minutes', return_value=45):
                status = await connector.get_session_status()
                
                assert isinstance(status, SessionStatus)
                assert status.is_valid is True
                assert status.expires_in_minutes == 45

    @pytest.mark.asyncio
    async def test_get_session_status_no_email(self, connector):
        connector.current_email = None
        
        status = await connector.get_session_status()
        
        assert isinstance(status, SessionStatus)
        assert status.is_valid is False
        assert status.expires_in_minutes == 0

    @pytest.mark.asyncio
    async def test_add_favorite_court(self, connector):
        connector.current_email = "test@example.com"
        
        with patch.object(connector.session_storage, 'add_favorite') as mock_add:
            favorite = await connector.add_favorite_court(
                name="Test Court",
                location="Test Location",
                court_type="futbol5",
                preferred_days=["mon", "wed"],
                preferred_time="evening"
            )
            
            assert isinstance(favorite, FavoriteCourt)
            assert favorite.name == "Test Court"
            assert favorite.location == "Test Location"
            assert favorite.court_type == "futbol5"
            assert favorite.preferred_days == ["mon", "wed"]
            assert favorite.preferred_time == "evening"
            mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_favorite_court_not_logged_in(self, connector):
        connector.current_email = None
        
        with pytest.raises(Exception, match="Not logged in"):
            await connector.add_favorite_court(
                name="Test Court",
                location="Test Location",
                court_type="futbol5",
                preferred_days=["mon"]
            )

    @pytest.mark.asyncio
    async def test_view_favorite_courts(self, connector):
        connector.current_email = "test@example.com"
        mock_favorites = [
            {
                "id": "1",
                "name": "Court 1",
                "location": "Location 1",
                "court_type": "futbol5",
                "preferred_days": ["mon"],
                "preferred_time": "evening"
            }
        ]
        
        with patch.object(connector.session_storage, 'get_favorites', return_value=mock_favorites):
            favorites = await connector.view_favorite_courts()
            
            assert len(favorites) == 1
            assert isinstance(favorites[0], FavoriteCourt)
            assert favorites[0].name == "Court 1"

    @pytest.mark.asyncio
    async def test_edit_favorite_court(self, connector):
        connector.current_email = "test@example.com"
        court_id = "1"
        updates = {"preferred_days": ["tue", "thu"]}
        
        mock_favorites = [
            FavoriteCourt(
                id="1",
                name="Court 1",
                location="Location 1",
                court_type="futbol5",
                preferred_days=["mon"],
                preferred_time="evening"
            )
        ]
        
        with patch.object(connector, 'view_favorite_courts', return_value=mock_favorites):
            with patch.object(connector.session_storage, 'save_favorites') as mock_save:
                updated = await connector.edit_favorite_court(court_id, updates)
                
                assert updated.preferred_days == ["tue", "thu"]
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_favorite_court(self, connector):
        connector.current_email = "test@example.com"
        court_id = "1"
        
        with patch.object(connector.session_storage, 'remove_favorite') as mock_remove:
            result = await connector.remove_favorite_court(court_id)
            
            assert result["status"] == "success"
            mock_remove.assert_called_once_with("test@example.com", court_id)

    @pytest.mark.asyncio
    async def test_check_availability_by_neighborhood(self, connector, mock_browser):
        mock_browser.execute_script.return_value = [
            {
                "court_id": "1",
                "court_name": "Court 1",
                "location": "Location 1",
                "court_type": "futbol5",
                "date": "2024-01-20",
                "time_slots": ["19:00", "20:00"],
                "price_per_hour": 5000.0,
                "address": "Address 1",
                "neighborhood": "Palermo"
            }
        ]
        
        availabilities = await connector.check_availability_by_neighborhood(
            neighborhood="Palermo",
            date="2024-01-20"
        )
        
        assert len(availabilities) == 1
        assert isinstance(availabilities[0], CourtAvailability)
        assert availabilities[0].court_name == "Court 1"
        assert availabilities[0].neighborhood == "Palermo"

    @pytest.mark.asyncio
    async def test_book_court_by_id(self, connector):
        booking = await connector.book_court_by_id(
            court_id="1",
            date="2024-01-20",
            time_slot="19:00",
            duration_hours=2,
            player_count=10
        )
        
        assert isinstance(booking, Booking)
        assert booking.court_id == "1"
        assert booking.date == "2024-01-20"
        assert booking.time_slot == "19:00"
        assert booking.duration_hours == 2
        assert booking.total_price == 200.0
        assert booking.status == "active"

    @pytest.mark.asyncio
    async def test_cancel_booking(self, connector):
        result = await connector.cancel_booking("booking123", "Player injured")
        
        assert result["status"] == "success"
        assert "booking123" in result["message"]
        assert result["reason"] == "Player injured"

    @pytest.mark.asyncio
    async def test_check_availability_by_max_price(self, connector):
        mock_courts = [
            CourtAvailability(
                court_id="1",
                court_name="Cheap Court",
                location="Location 1",
                court_type="futbol5",
                date="2024-01-20",
                time_slots=["19:00"],
                price_per_hour=4000.0,
                address="Address 1"
            ),
            CourtAvailability(
                court_id="2",
                court_name="Expensive Court",
                location="Location 2",
                court_type="futbol5",
                date="2024-01-20",
                time_slots=["19:00"],
                price_per_hour=8000.0,
                address="Address 2"
            )
        ]
        
        with patch.object(connector, 'check_availability_by_date', return_value=mock_courts):
            filtered = await connector.check_availability_by_max_price(
                max_price=5000.0,
                date="2024-01-20"
            )
            
            assert len(filtered) == 1
            assert filtered[0].court_name == "Cheap Court"