"""Tests for session storage."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.connectors.afip.interfaces import AFIPSession
from src.connectors.afip.session.storage import EncryptedSessionStorage, InMemorySessionStorage


class TestInMemorySessionStorage:
    """Tests for in-memory storage."""
    
    @pytest.fixture
    def storage(self):
        """Creates an in-memory storage."""
        return InMemorySessionStorage()
    
    @pytest.fixture
    def sample_session(self):
        """Creates a sample session."""
        return AFIPSession(
            session_id="test_session_123",
            cuit="20-12345678-9",
            cookies={"session": "abc123", "token": "xyz789"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=True
        )
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, storage, sample_session):
        """Verifies saving and loading a session."""
        # Save
        result = await storage.save(sample_session)
        assert result is True
        
        # Load
        loaded = await storage.load(sample_session.cuit)
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.cuit == sample_session.cuit
        assert loaded.cookies == sample_session.cookies
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, storage):
        """Verifies loading a non-existent session."""
        loaded = await storage.load("99-99999999-9")
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self, storage, sample_session):
        """Verifies deleting a session."""
        # Save
        await storage.save(sample_session)
        
        # Delete
        result = await storage.delete(sample_session.cuit)
        assert result is True
        
        # Verify it doesn't exist
        loaded = await storage.load(sample_session.cuit)
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, storage):
        """Verifies deleting a non-existent session."""
        result = await storage.delete("99-99999999-9")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_valid_with_valid_session(self, storage, sample_session):
        """Verifies validation of a valid session."""
        is_valid = await storage.is_valid(sample_session)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_is_valid_with_expired_session(self, storage):
        """Verifies validation of an expired session."""
        expired_session = AFIPSession(
            session_id="expired_123",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now() - timedelta(hours=3),
            expires_at=datetime.now() - timedelta(hours=1),
            is_valid=True
        )
        
        is_valid = await storage.is_valid(expired_session)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_is_valid_with_invalid_session(self, storage):
        """Verifies validation of a session marked as invalid."""
        invalid_session = AFIPSession(
            session_id="invalid_123",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=False
        )
        
        is_valid = await storage.is_valid(invalid_session)
        assert is_valid is False


class TestEncryptedSessionStorage:
    """Tests for encrypted storage."""
    
    @pytest.fixture
    def temp_dir(self):
        """Creates a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Creates an encrypted storage."""
        return EncryptedSessionStorage(temp_dir)
    
    @pytest.fixture
    def sample_session(self):
        """Creates a sample session."""
        return AFIPSession(
            session_id="encrypted_session_123",
            cuit="20-12345678-9",
            cookies={"session": "abc123", "token": "xyz789"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=True
        )
    
    @pytest.mark.asyncio
    async def test_save_creates_encrypted_file(self, storage, sample_session, temp_dir):
        """Verifies that an encrypted file is created."""
        result = await storage.save(sample_session)
        assert result is True
        
        # Verify that the file exists
        session_path = Path(temp_dir) / "session_20123456789.enc"
        assert session_path.exists()
        
        # Verify it's encrypted (doesn't contain plain text)
        content = session_path.read_bytes()
        assert b"abc123" not in content  # Cookie should not be in plain text
        assert b"20-12345678-9" not in content  # CUIT should not be in plain text
    
    @pytest.mark.asyncio
    async def test_load_decrypts_correctly(self, storage, sample_session):
        """Verifies that loading decrypts correctly."""
        # Save
        await storage.save(sample_session)
        
        # Load
        loaded = await storage.load(sample_session.cuit)
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.cookies == sample_session.cookies
        assert loaded.cuit == sample_session.cuit
    
    @pytest.mark.asyncio
    async def test_encryption_key_generation(self, temp_dir):
        """Verifies automatic encryption key generation."""
        storage = EncryptedSessionStorage(temp_dir)
        
        # Verify that the key was generated
        key_path = Path(temp_dir) / ".encryption_key"
        assert key_path.exists()
        
        # Verify restrictive permissions
        stat_info = os.stat(key_path)
        assert stat_info.st_mode & 0o777 == 0o600
    
    @pytest.mark.asyncio
    async def test_custom_encryption_key(self, temp_dir, sample_session):
        """Verifies the use of a custom encryption key."""
        from cryptography.fernet import Fernet
        
        # Generate custom key
        custom_key = Fernet.generate_key()
        
        # Create storage with custom key
        storage = EncryptedSessionStorage(temp_dir, custom_key)
        
        # Save and load
        await storage.save(sample_session)
        loaded = await storage.load(sample_session.cuit)
        
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
    
    @pytest.mark.asyncio
    async def test_file_permissions(self, storage, sample_session, temp_dir):
        """Verifies that files have restrictive permissions."""
        await storage.save(sample_session)
        
        session_path = Path(temp_dir) / "session_20123456789.enc"
        stat_info = os.stat(session_path)
        
        # Verify that only the owner can read/write
        assert stat_info.st_mode & 0o777 == 0o600
    
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, storage, temp_dir):
        """Verifies handling of corrupted files."""
        # Create corrupted file
        corrupted_path = Path(temp_dir) / "session_20999999999.enc"
        corrupted_path.write_bytes(b"corrupted data")
        
        # Try to load
        loaded = await storage.load("20-99999999-9")
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_expired_session_invalidation(self, storage):
        """Verifies that expired sessions are marked as invalid."""
        expired_session = AFIPSession(
            session_id="expired_123",
            cuit="20-88888888-8",
            cookies={},
            created_at=datetime.now() - timedelta(hours=3),
            expires_at=datetime.now() - timedelta(hours=1),
            is_valid=True
        )
        
        # Save expired session
        await storage.save(expired_session)
        
        # Verify validity
        is_valid = await storage.is_valid(expired_session)
        assert is_valid is False
        
        # Load and verify it was marked as invalid
        loaded = await storage.load(expired_session.cuit)
        assert loaded is not None
        assert loaded.is_valid is False