from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.logger import get_logger

logger = get_logger(__name__)


class ATCSportsSessionStorage:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".atc_sports" / "sessions.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._session_data: Dict[str, Any] = {}
        self._load_session()

    def _load_session(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._session_data = json.load(f)
                logger.info("Session data loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load session data: {e}")
                self._session_data = {}

    def _save_session(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self._session_data, f, indent=2)
            logger.info("Session data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")

    def save_session_token(self, email: str, token: str, expires_in_seconds: int = 3600) -> None:
        expiry = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        self._session_data[email] = {
            "token": token,
            "expires_at": expiry.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        self._save_session()
        logger.info(f"Session token saved for {email}")

    def get_session_token(self, email: str) -> Optional[str]:
        session = self._session_data.get(email)
        if not session:
            logger.warning(f"No session found for {email}")
            return None

        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning(f"Session expired for {email}")
            self.clear_session(email)
            return None

        return session["token"]

    def is_session_valid(self, email: str) -> bool:
        session = self._session_data.get(email)
        if not session:
            return False

        expires_at = datetime.fromisoformat(session["expires_at"])
        return datetime.utcnow() < expires_at

    def get_session_expires_in_minutes(self, email: str) -> int:
        session = self._session_data.get(email)
        if not session:
            return 0

        expires_at = datetime.fromisoformat(session["expires_at"])
        remaining = expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))

    def refresh_session(self, email: str, new_token: str, expires_in_seconds: int = 3600) -> None:
        self.save_session_token(email, new_token, expires_in_seconds)
        logger.info(f"Session refreshed for {email}")

    def clear_session(self, email: str) -> None:
        if email in self._session_data:
            del self._session_data[email]
            self._save_session()
            logger.info(f"Session cleared for {email}")

    def clear_all_sessions(self) -> None:
        self._session_data = {}
        self._save_session()
        logger.info("All sessions cleared")

    def get_all_sessions(self) -> Dict[str, Any]:
        return self._session_data.copy()

    def save_favorites(self, email: str, favorites: list) -> None:
        if email not in self._session_data:
            self._session_data[email] = {}
        self._session_data[email]["favorites"] = favorites
        self._save_session()
        logger.info(f"Favorites saved for {email}")

    def get_favorites(self, email: str) -> list:
        session = self._session_data.get(email, {})
        return session.get("favorites", [])

    def add_favorite(self, email: str, favorite: dict) -> None:
        favorites = self.get_favorites(email)
        favorites.append(favorite)
        self.save_favorites(email, favorites)

    def remove_favorite(self, email: str, court_id: str) -> None:
        favorites = self.get_favorites(email)
        favorites = [f for f in favorites if f.get("id") != court_id]
        self.save_favorites(email, favorites)