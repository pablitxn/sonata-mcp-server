from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CourtType(Enum):
    FUTBOL5 = "futbol5"
    FUTBOL7 = "futbol7"
    TENNIS = "tennis"
    PADDLE = "paddle"


class TimePreference(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


@dataclass
class SessionStatus:
    is_valid: bool
    expires_in_minutes: int


@dataclass
class FavoriteCourt:
    id: str
    name: str
    location: str
    court_type: CourtType
    preferred_days: List[str]
    preferred_time: Optional[TimePreference] = None


@dataclass
class CourtAvailability:
    court_id: str
    court_name: str
    location: str
    court_type: CourtType
    date: str
    time_slots: List[str]
    price_per_hour: float
    address: str
    neighborhood: Optional[str] = None


@dataclass
class Booking:
    booking_id: str
    court_id: str
    court_name: str
    location: str
    date: str
    time_slot: str
    duration_hours: int
    total_price: float
    player_count: Optional[int] = None
    confirmation_code: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None


@dataclass
class TimeRange:
    from_time: str
    to_time: str


@dataclass
class DateRange:
    from_date: str
    to_date: str


@dataclass
class Coordinates:
    lat: float
    lng: float


class IATCSportsConnector(ABC):
    @abstractmethod
    async def login_request(self, email: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def login_with_url(self, magic_link_url: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def refresh_session(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def logout(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_session_status(self) -> SessionStatus:
        pass

    @abstractmethod
    async def add_favorite_court(
        self,
        name: str,
        location: str,
        court_type: str,
        preferred_days: List[str],
        preferred_time: Optional[str] = None
    ) -> FavoriteCourt:
        pass

    @abstractmethod
    async def view_favorite_courts(self) -> List[FavoriteCourt]:
        pass

    @abstractmethod
    async def edit_favorite_court(
        self,
        court_id: str,
        updates: Dict[str, Any]
    ) -> FavoriteCourt:
        pass

    @abstractmethod
    async def remove_favorite_court(self, court_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def check_availability_by_neighborhood(
        self,
        neighborhood: str,
        date: str,
        time_range: Optional[TimeRange] = None,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def check_availability_by_date(
        self,
        date: str,
        time_slot: Optional[str] = None,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def check_availability_by_favorites(
        self,
        date_range: DateRange,
        time_preference: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def check_availability_by_type(
        self,
        court_type: str,
        date: str,
        neighborhood: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def check_availability_by_max_price(
        self,
        max_price: float,
        date: str,
        time_slot: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def check_availability_by_time(
        self,
        time_slot: str,
        date_range: DateRange,
        court_type: Optional[str] = None
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def search_courts_near(
        self,
        address: Optional[str] = None,
        coordinates: Optional[Coordinates] = None,
        radius_km: float = 5.0
    ) -> List[CourtAvailability]:
        pass

    @abstractmethod
    async def book_court_by_id(
        self,
        court_id: str,
        date: str,
        time_slot: str,
        duration_hours: int,
        player_count: Optional[int] = None
    ) -> Booking:
        pass

    @abstractmethod
    async def cancel_booking(
        self,
        booking_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def view_active_bookings(self) -> List[Booking]:
        pass

    @abstractmethod
    async def view_booking_history(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Booking]:
        pass

    @abstractmethod
    async def view_booking_details(self, booking_id: str) -> Booking:
        pass