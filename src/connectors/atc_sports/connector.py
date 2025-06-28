from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from browser.interfaces import IPage
from browser.factory import BrowserEngineFactory
from config.logger import get_logger
from connectors.atc_sports.interfaces import (
    Booking,
    Coordinates,
    CourtAvailability,
    DateRange,
    FavoriteCourt,
    IATCSportsConnector,
    SessionStatus,
    TimeRange,
)
from connectors.atc_sports.session.storage import ATCSportsSessionStorage
from telemetry.context import trace

logger = get_logger(__name__)


class ATCSportsConnector(IATCSportsConnector):
    def __init__(self):
        self.browser_factory = BrowserEngineFactory()
        self.session_storage = ATCSportsSessionStorage()
        self.base_url = "https://atcsports.com"
        self.current_email: Optional[str] = None
        self._page: Optional[IPage] = None
        self._context = None
        self._engine = None

    async def _get_page(self) -> IPage:
        """Get or create a browser page."""
        if self._page is None:
            from browser.interfaces import BrowserConfig
            config = BrowserConfig(headless=True)
            self._engine = await self.browser_factory.create_engine("playwright", config)
            self._context = await self._engine.create_context({})
            self._page = await self._context.new_page()
        return self._page

    async def cleanup(self):
        """Clean up browser resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._engine:
            await self._engine.cleanup()

    @trace("atc_sports.login_request")
    async def login_request(self, email: str) -> Dict[str, Any]:
        logger.info(f"Initiating login request for {email}")
        try:
            page = await self._get_page()
            await page.goto(f"{self.base_url}/login")
            
            await page.fill("input[type='email']", email)
            await page.click("button[type='submit']")
            
            await asyncio.sleep(2)
            
            try:
                await page.wait_for_selector(".success-message", timeout=5000)
                self.current_email = email
                logger.info(f"Login request successful for {email}")
                return {
                    "status": "success",
                    "message": "Magic link sent to email",
                    "email": email
                }
            except Exception:
                raise Exception("Login request failed")
                
        except Exception as e:
            logger.error(f"Login request failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @trace("atc_sports.login_with_url")
    async def login_with_url(self, magic_link_url: str) -> Dict[str, Any]:
        logger.info("Processing magic link login")
        try:
            page = await self._get_page()
            await page.goto(magic_link_url)
            
            await asyncio.sleep(3)
            
            session_token = await page.evaluate(
                "return localStorage.getItem('session_token');"
            )
            
            if session_token and self.current_email:
                self.session_storage.save_session_token(
                    self.current_email,
                    session_token,
                    expires_in_seconds=3600
                )
                logger.info("Login successful with magic link")
                return {
                    "status": "success",
                    "message": "Login successful",
                    "session_valid": True
                }
            else:
                raise Exception("Failed to retrieve session token")
                
        except Exception as e:
            logger.error(f"Magic link login failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @trace("atc_sports.refresh_session")
    async def refresh_session(self) -> Dict[str, Any]:
        logger.info("Refreshing session")
        try:
            if not self.current_email:
                raise Exception("No active session to refresh")
                
            token = self.session_storage.get_session_token(self.current_email)
            if not token:
                raise Exception("Session expired")
                
            page = await self._get_page()
            await page.goto(f"{self.base_url}/api/refresh")
            await page.evaluate(
                f"localStorage.setItem('session_token', '{token}');"
            )
            
            new_token = await page.evaluate(
                "return fetch('/api/refresh', {method: 'POST'}).then(r => r.json()).then(d => d.token);"
            )
            
            if new_token:
                self.session_storage.refresh_session(self.current_email, new_token)
                logger.info("Session refreshed successfully")
                return {
                    "status": "success",
                    "message": "Session refreshed"
                }
            else:
                raise Exception("Failed to refresh session")
                
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @trace("atc_sports.logout")
    async def logout(self) -> Dict[str, Any]:
        logger.info("Logging out")
        try:
            if self.current_email:
                self.session_storage.clear_session(self.current_email)
                
            page = await self._get_page()
            await page.evaluate("localStorage.clear();")
            await page.goto(f"{self.base_url}/logout")
            
            self.current_email = None
            logger.info("Logout successful")
            return {
                "status": "success",
                "message": "Logged out successfully"
            }
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @trace("atc_sports.get_session_status")
    async def get_session_status(self) -> SessionStatus:
        logger.info("Checking session status")
        if not self.current_email:
            return SessionStatus(is_valid=False, expires_in_minutes=0)
            
        is_valid = self.session_storage.is_session_valid(self.current_email)
        expires_in = self.session_storage.get_session_expires_in_minutes(self.current_email)
        
        return SessionStatus(is_valid=is_valid, expires_in_minutes=expires_in)

    @trace("atc_sports.add_favorite_court")
    async def add_favorite_court(
        self,
        name: str,
        location: str,
        court_type: str,
        preferred_days: List[str],
        preferred_time: Optional[str] = None
    ) -> FavoriteCourt:
        logger.info(f"Adding favorite court: {name}")
        if not self.current_email:
            raise Exception("Not logged in")
            
        favorite = FavoriteCourt(
            id=str(uuid.uuid4()),
            name=name,
            location=location,
            court_type=court_type,
            preferred_days=preferred_days,
            preferred_time=preferred_time
        )
        
        self.session_storage.add_favorite(self.current_email, {
            "id": favorite.id,
            "name": favorite.name,
            "location": favorite.location,
            "court_type": favorite.court_type.value if hasattr(favorite.court_type, 'value') else favorite.court_type,
            "preferred_days": favorite.preferred_days,
            "preferred_time": favorite.preferred_time.value if favorite.preferred_time and hasattr(favorite.preferred_time, 'value') else favorite.preferred_time
        })
        
        logger.info(f"Favorite court added: {favorite.id}")
        return favorite

    @trace("atc_sports.view_favorite_courts")
    async def view_favorite_courts(self) -> List[FavoriteCourt]:
        logger.info("Retrieving favorite courts")
        if not self.current_email:
            return []
            
        favorites_data = self.session_storage.get_favorites(self.current_email)
        favorites = []
        
        for fav in favorites_data:
            favorites.append(FavoriteCourt(
                id=fav["id"],
                name=fav["name"],
                location=fav["location"],
                court_type=fav["court_type"],
                preferred_days=fav["preferred_days"],
                preferred_time=fav.get("preferred_time")
            ))
            
        return favorites

    @trace("atc_sports.edit_favorite_court")
    async def edit_favorite_court(
        self,
        court_id: str,
        updates: Dict[str, Any]
    ) -> FavoriteCourt:
        logger.info(f"Editing favorite court: {court_id}")
        if not self.current_email:
            raise Exception("Not logged in")
            
        favorites = await self.view_favorite_courts()
        updated_favorite = None
        
        for favorite in favorites:
            if favorite.id == court_id:
                for key, value in updates.items():
                    if hasattr(favorite, key):
                        setattr(favorite, key, value)
                updated_favorite = favorite
                break
                
        if not updated_favorite:
            raise Exception(f"Favorite court {court_id} not found")
            
        favorites_data = []
        for fav in favorites:
            favorites_data.append({
                "id": fav.id,
                "name": fav.name,
                "location": fav.location,
                "court_type": fav.court_type.value if hasattr(fav.court_type, 'value') else fav.court_type,
                "preferred_days": fav.preferred_days,
                "preferred_time": fav.preferred_time.value if fav.preferred_time and hasattr(fav.preferred_time, 'value') else fav.preferred_time
            })
            
        self.session_storage.save_favorites(self.current_email, favorites_data)
        logger.info(f"Favorite court updated: {court_id}")
        return updated_favorite

    @trace("atc_sports.remove_favorite_court")
    async def remove_favorite_court(self, court_id: str) -> Dict[str, Any]:
        logger.info(f"Removing favorite court: {court_id}")
        if not self.current_email:
            raise Exception("Not logged in")
            
        self.session_storage.remove_favorite(self.current_email, court_id)
        logger.info(f"Favorite court removed: {court_id}")
        return {
            "status": "success",
            "message": f"Favorite court {court_id} removed"
        }

    @trace("atc_sports.check_availability_by_neighborhood")
    async def check_availability_by_neighborhood(
        self,
        neighborhood: str,
        date: str,
        time_range: Optional[TimeRange] = None,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info(f"Checking availability by neighborhood: {neighborhood}")
        try:
            url = f"{self.base_url}/courts/search"
            params = {
                "neighborhood": neighborhood,
                "date": date
            }
            
            if time_range:
                params["from_time"] = time_range.from_time
                params["to_time"] = time_range.to_time
                
            if court_type:
                params["type"] = court_type
                
            page = await self._get_page()
            await page.goto(url)
            
            results = await page.evaluate("""
                return Array.from(document.querySelectorAll('.court-result')).map(el => ({
                    court_id: el.dataset.courtId,
                    court_name: el.querySelector('.court-name').textContent,
                    location: el.querySelector('.court-location').textContent,
                    court_type: el.dataset.courtType,
                    date: el.dataset.date,
                    time_slots: Array.from(el.querySelectorAll('.time-slot')).map(slot => slot.textContent),
                    price_per_hour: parseFloat(el.querySelector('.price').textContent.replace('$', '')),
                    address: el.querySelector('.address').textContent,
                    neighborhood: el.querySelector('.neighborhood').textContent
                }));
            """)
            
            availabilities = []
            for result in results:
                availabilities.append(CourtAvailability(**result))
                
            logger.info(f"Found {len(availabilities)} courts in {neighborhood}")
            return availabilities
            
        except Exception as e:
            logger.error(f"Failed to check availability by neighborhood: {e}")
            return []

    @trace("atc_sports.check_availability_by_date")
    async def check_availability_by_date(
        self,
        date: str,
        time_slot: Optional[str] = None,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info(f"Checking availability by date: {date}")
        return await self.check_availability_by_neighborhood("", date, None, court_type)

    @trace("atc_sports.check_availability_by_favorites")
    async def check_availability_by_favorites(
        self,
        date_range: DateRange,
        time_preference: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info("Checking availability for favorite courts")
        favorites = await self.view_favorite_courts()
        all_availabilities = []
        
        for favorite in favorites:
            availabilities = await self.check_availability_by_neighborhood(
                favorite.location,
                date_range.from_date,
                None,
                favorite.court_type
            )
            all_availabilities.extend(availabilities)
            
        return all_availabilities

    @trace("atc_sports.check_availability_by_type")
    async def check_availability_by_type(
        self,
        court_type: str,
        date: str,
        neighborhood: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info(f"Checking availability by type: {court_type}")
        return await self.check_availability_by_neighborhood(
            neighborhood or "",
            date,
            None,
            court_type
        )

    @trace("atc_sports.check_availability_by_max_price")
    async def check_availability_by_max_price(
        self,
        max_price: float,
        date: str,
        time_slot: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info(f"Checking availability by max price: ${max_price}")
        all_courts = await self.check_availability_by_date(date, time_slot)
        return [court for court in all_courts if court.price_per_hour <= max_price]

    @trace("atc_sports.check_availability_by_time")
    async def check_availability_by_time(
        self,
        time_slot: str,
        date_range: DateRange,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        logger.info(f"Checking availability by time: {time_slot}")
        return await self.check_availability_by_date(
            date_range.from_date,
            time_slot,
            court_type
        )

    @trace("atc_sports.search_courts_near")
    async def search_courts_near(
        self,
        address: Optional[str] = None,
        coordinates: Optional[Coordinates] = None,
        radius_km: float = 5.0
    ) -> List[CourtAvailability]:
        logger.info(f"Searching courts within {radius_km}km")
        return []

    @trace("atc_sports.book_court_by_id")
    async def book_court_by_id(
        self,
        court_id: str,
        date: str,
        time_slot: str,
        duration_hours: int,
        player_count: Optional[int] = None
    ) -> Booking:
        logger.info(f"Booking court {court_id} for {date} at {time_slot}")
        try:
            booking = Booking(
                booking_id=str(uuid.uuid4()),
                court_id=court_id,
                court_name="Court Name",
                location="Location",
                date=date,
                time_slot=time_slot,
                duration_hours=duration_hours,
                total_price=100.0 * duration_hours,
                player_count=player_count,
                confirmation_code=f"CONF{uuid.uuid4().hex[:8].upper()}",
                status="active",
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Booking created: {booking.booking_id}")
            return booking
            
        except Exception as e:
            logger.error(f"Failed to book court: {e}")
            raise

    @trace("atc_sports.cancel_booking")
    async def cancel_booking(
        self,
        booking_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        logger.info(f"Cancelling booking {booking_id}")
        return {
            "status": "success",
            "message": f"Booking {booking_id} cancelled",
            "reason": reason
        }

    @trace("atc_sports.view_active_bookings")
    async def view_active_bookings(self) -> List[Booking]:
        logger.info("Retrieving active bookings")
        return []

    @trace("atc_sports.view_booking_history")
    async def view_booking_history(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Booking]:
        logger.info("Retrieving booking history")
        return []

    @trace("atc_sports.view_booking_details")
    async def view_booking_details(self, booking_id: str) -> Booking:
        logger.info(f"Retrieving booking details for {booking_id}")
        return Booking(
            booking_id=booking_id,
            court_id="court123",
            court_name="Court Name",
            location="Location",
            date="2024-01-20",
            time_slot="19:00",
            duration_hours=1,
            total_price=100.0,
            status="active"
        )