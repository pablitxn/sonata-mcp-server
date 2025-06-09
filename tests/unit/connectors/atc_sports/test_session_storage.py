import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.connectors.atc_sports.session.storage import ATCSportsSessionStorage


class TestATCSportsSessionStorage:
    @pytest.fixture
    def temp_storage_path(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def storage(self, temp_storage_path):
        return ATCSportsSessionStorage(storage_path=temp_storage_path)

    def test_save_and_get_session_token(self, storage):
        email = "test@example.com"
        token = "test_token_123"
        expires_in = 3600

        storage.save_session_token(email, token, expires_in)
        retrieved_token = storage.get_session_token(email)

        assert retrieved_token == token

    def test_get_nonexistent_session_token(self, storage):
        token = storage.get_session_token("nonexistent@example.com")
        assert token is None

    def test_expired_session_token(self, storage):
        email = "test@example.com"
        token = "test_token_123"
        
        storage.save_session_token(email, token, expires_in_seconds=-1)
        
        retrieved_token = storage.get_session_token(email)
        assert retrieved_token is None

    def test_is_session_valid(self, storage):
        email = "test@example.com"
        token = "test_token_123"

        storage.save_session_token(email, token, expires_in_seconds=3600)
        assert storage.is_session_valid(email) is True

        storage.save_session_token(email, token, expires_in_seconds=-1)
        assert storage.is_session_valid(email) is False

    def test_get_session_expires_in_minutes(self, storage):
        email = "test@example.com"
        token = "test_token_123"
        expires_in_seconds = 3600

        storage.save_session_token(email, token, expires_in_seconds)
        
        minutes = storage.get_session_expires_in_minutes(email)
        assert 59 <= minutes <= 60

    def test_refresh_session(self, storage):
        email = "test@example.com"
        old_token = "old_token"
        new_token = "new_token"

        storage.save_session_token(email, old_token, expires_in_seconds=100)
        storage.refresh_session(email, new_token, expires_in_seconds=3600)

        retrieved_token = storage.get_session_token(email)
        assert retrieved_token == new_token

    def test_clear_session(self, storage):
        email = "test@example.com"
        token = "test_token_123"

        storage.save_session_token(email, token)
        storage.clear_session(email)

        assert storage.get_session_token(email) is None

    def test_clear_all_sessions(self, storage):
        emails = ["test1@example.com", "test2@example.com"]
        
        for email in emails:
            storage.save_session_token(email, f"token_{email}")

        storage.clear_all_sessions()

        for email in emails:
            assert storage.get_session_token(email) is None

    def test_save_and_get_favorites(self, storage):
        email = "test@example.com"
        favorites = [
            {"id": "1", "name": "Court 1", "location": "Location 1"},
            {"id": "2", "name": "Court 2", "location": "Location 2"}
        ]

        storage.save_favorites(email, favorites)
        retrieved_favorites = storage.get_favorites(email)

        assert retrieved_favorites == favorites

    def test_add_favorite(self, storage):
        email = "test@example.com"
        favorite = {"id": "1", "name": "Court 1", "location": "Location 1"}

        storage.add_favorite(email, favorite)
        favorites = storage.get_favorites(email)

        assert len(favorites) == 1
        assert favorites[0] == favorite

    def test_remove_favorite(self, storage):
        email = "test@example.com"
        favorites = [
            {"id": "1", "name": "Court 1", "location": "Location 1"},
            {"id": "2", "name": "Court 2", "location": "Location 2"}
        ]

        storage.save_favorites(email, favorites)
        storage.remove_favorite(email, "1")

        remaining_favorites = storage.get_favorites(email)
        assert len(remaining_favorites) == 1
        assert remaining_favorites[0]["id"] == "2"

    def test_persistence(self, temp_storage_path):
        email = "test@example.com"
        token = "test_token_123"
        favorites = [{"id": "1", "name": "Court 1"}]

        storage1 = ATCSportsSessionStorage(storage_path=temp_storage_path)
        storage1.save_session_token(email, token, expires_in_seconds=3600)
        storage1.save_favorites(email, favorites)

        storage2 = ATCSportsSessionStorage(storage_path=temp_storage_path)
        assert storage2.get_session_token(email) == token
        assert storage2.get_favorites(email) == favorites