import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.atc_sports.connector import ATCSportsConnector
from src.connectors.atc_sports.interfaces import (
    DateRange,
    TimeRange,
)


@pytest.mark.integration
class TestATCSportsIntegration:
    @pytest.fixture
    async def connector(self):
        connector = ATCSportsConnector()
        yield connector
        await connector.cleanup()

    @pytest.mark.asyncio
    async def test_full_booking_flow(self, connector):
        mock_page = Mock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.evaluate = AsyncMock()
        
        with patch.object(connector, '_get_page', new_callable=AsyncMock, return_value=mock_page):
            mock_page.evaluate.side_effect = [
                "session_token_123",
                [
                    {
                        "court_id": "court1",
                        "court_name": "Test Court",
                        "location": "Test Location",
                        "court_type": "futbol5",
                        "date": "2024-01-20",
                        "time_slots": ["19:00", "20:00"],
                        "price_per_hour": 5000.0,
                        "address": "Test Address",
                        "neighborhood": "Palermo"
                    }
                ]
            ]
            
            login_result = await connector.login_request("test@example.com")
            assert login_result["status"] == "success"
            
            magic_link = "https://atcsports.com/login?token=abc123"
            login_url_result = await connector.login_with_url(magic_link)
            assert login_url_result["status"] == "success"
            
            courts = await connector.check_availability_by_neighborhood(
                "Palermo", 
                "2024-01-20"
            )
            assert len(courts) == 1
            assert courts[0].court_name == "Test Court"
            
            booking = await connector.book_court_by_id(
                "court1",
                "2024-01-20",
                "19:00",
                1,
                10
            )
            assert booking.court_id == "court1"
            assert booking.status == "active"

    @pytest.mark.asyncio
    async def test_favorite_courts_management(self, connector):
        connector.current_email = "test@example.com"
        
        favorite = await connector.add_favorite_court(
            name="My Favorite Court",
            location="Palermo",
            court_type="futbol5",
            preferred_days=["mon", "wed", "fri"],
            preferred_time="evening"
        )
        assert favorite.name == "My Favorite Court"
        
        favorites = await connector.view_favorite_courts()
        assert len(favorites) == 1
        assert favorites[0].id == favorite.id
        
        updated = await connector.edit_favorite_court(
            favorite.id,
            {"preferred_days": ["tue", "thu"]}
        )
        assert updated.preferred_days == ["tue", "thu"]
        
        remove_result = await connector.remove_favorite_court(favorite.id)
        assert remove_result["status"] == "success"
        
        favorites_after = await connector.view_favorite_courts()
        assert len(favorites_after) == 0

    @pytest.mark.asyncio
    async def test_availability_search_variations(self, connector):
        mock_page = Mock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        
        with patch.object(connector, '_get_page', new_callable=AsyncMock, return_value=mock_page):
            mock_page.evaluate.return_value = [
                    {
                        "court_id": "1",
                        "court_name": "Court 1",
                        "location": "Location 1",
                        "court_type": "futbol5",
                        "date": "2024-01-20",
                        "time_slots": ["19:00"],
                        "price_per_hour": 4000.0,
                        "address": "Address 1",
                        "neighborhood": "Palermo"
                    },
                    {
                        "court_id": "2",
                        "court_name": "Court 2",
                        "location": "Location 2",
                        "court_type": "tennis",
                        "date": "2024-01-20",
                        "time_slots": ["20:00"],
                        "price_per_hour": 6000.0,
                        "address": "Address 2",
                        "neighborhood": "Recoleta"
                    }
                ]
            
            by_neighborhood = await connector.check_availability_by_neighborhood(
                "Palermo",
                "2024-01-20",
                TimeRange(from_time="18:00", to_time="22:00")
            )
            assert len(by_neighborhood) == 2
            
            by_type = await connector.check_availability_by_type(
                "futbol5",
                "2024-01-20",
                "Palermo"
            )
            assert len(by_type) == 2
            
            by_price = await connector.check_availability_by_max_price(
                5000.0,
                "2024-01-20"
            )
            assert len(by_price) == 1
            assert by_price[0].price_per_hour <= 5000.0

    @pytest.mark.asyncio
    async def test_session_management(self, connector):
        initial_status = await connector.get_session_status()
        assert initial_status.is_valid is False
        
        connector.current_email = "test@example.com"
        connector.session_storage.save_session_token(
            "test@example.com",
            "test_token",
            expires_in_seconds=3600
        )
        
        status_after_save = await connector.get_session_status()
        assert status_after_save.is_valid is True
        assert status_after_save.expires_in_minutes > 0
        
        mock_page = Mock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock()
        
        with patch.object(connector, '_get_page', new_callable=AsyncMock, return_value=mock_page):
            mock_page.evaluate.side_effect = ["test_token", "new_token"]
            
            refresh_result = await connector.refresh_session()
            assert refresh_result["status"] == "success"
        
        logout_result = await connector.logout()
        assert logout_result["status"] == "success"
        assert connector.current_email is None
        
        final_status = await connector.get_session_status()
        assert final_status.is_valid is False

    @pytest.mark.asyncio
    async def test_booking_history_and_cancellation(self, connector):
        with patch.object(connector, 'view_active_bookings', new_callable=AsyncMock) as mock_active:
            with patch.object(connector, 'view_booking_history', new_callable=AsyncMock) as mock_history:
                mock_active.return_value = [
                    {
                        "booking_id": "active1",
                        "court_name": "Active Court",
                        "date": "2024-01-25",
                        "time_slot": "19:00"
                    }
                ]
                
                mock_history.return_value = [
                    {
                        "booking_id": "past1",
                        "court_name": "Past Court",
                        "date": "2024-01-10",
                        "time_slot": "20:00"
                    }
                ]
                
                active_bookings = await connector.view_active_bookings()
                assert len(active_bookings) == 1
                
                history = await connector.view_booking_history(
                    from_date="2024-01-01",
                    to_date="2024-01-31"
                )
                assert len(history) == 1
                
                cancel_result = await connector.cancel_booking(
                    "active1",
                    "Weather conditions"
                )
                assert cancel_result["status"] == "success"
                assert cancel_result["reason"] == "Weather conditions"

    @pytest.mark.asyncio 
    async def test_error_handling(self, connector):
        with pytest.raises(Exception, match="Not logged in"):
            await connector.add_favorite_court(
                name="Test",
                location="Test",
                court_type="futbol5",
                preferred_days=["mon"]
            )
        
        mock_page = Mock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
        with patch.object(connector, '_get_page', new_callable=AsyncMock, return_value=mock_page):
            result = await connector.login_request("test@example.com")
            assert result["status"] == "error"
            assert "Network error" in result["message"]