"""Session storage implementations for AFIP connector.

This module provides different storage backends for AFIP session data:
- InMemorySessionStorage: Temporary storage in memory (mainly for testing)
- EncryptedSessionStorage: Persistent storage with encryption on disk

The storage implementations handle session persistence, validation, and lifecycle
management for AFIP authentication sessions.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from cryptography.fernet import Fernet

from ..interfaces import AFIPSession, ISessionStorage

logger = structlog.get_logger()


class InMemorySessionStorage(ISessionStorage):
    """In-memory session storage implementation.
    
    This storage backend keeps sessions in a simple dictionary in memory.
    It's primarily intended for testing scenarios where persistence is not
    required. All sessions are lost when the process terminates.
    
    Attributes:
        _sessions: Dictionary mapping CUIT to AFIPSession objects
        logger: Structured logger instance bound with storage type
    """
    
    def __init__(self):
        """Initialize the in-memory storage.
        
        Creates an empty sessions dictionary and configures the logger
        with the storage type for better log filtering and debugging.
        """
        self._sessions: Dict[str, AFIPSession] = {}
        self.logger = logger.bind(storage="memory")
    
    async def save(self, session: AFIPSession) -> bool:
        """Save a session in memory.
        
        Stores the session object in the internal dictionary using the CUIT
        as the key. This operation is always synchronous despite being async
        for interface compatibility.
        
        Args:
            session: AFIPSession object to save
            
        Returns:
            bool: True if saved successfully, False on error
        """
        try:
            # Store session using CUIT as unique identifier
            self._sessions[session.cuit] = session
            self.logger.info("session_saved", cuit=session.cuit)
            return True
        except Exception as e:
            # Log any unexpected errors during save operation
            self.logger.error("session_save_error", error=str(e))
            return False
    
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Load a session from memory.
        
        Retrieves a session from the internal dictionary using the CUIT.
        Returns None if the session doesn't exist.
        
        Args:
            cuit: CUIT identifier associated with the session
            
        Returns:
            Optional[AFIPSession]: The stored session or None if not found
        """
        # Attempt to retrieve session from dictionary
        session = self._sessions.get(cuit)
        
        if session:
            self.logger.info("session_loaded", cuit=cuit)
        else:
            # Use debug level for not found as it's often expected behavior
            self.logger.debug("session_not_found", cuit=cuit)
        
        return session
    
    async def delete(self, cuit: str) -> bool:
        """Delete a session from memory.
        
        Removes the session from the internal dictionary. This is useful
        for explicit logout operations or session cleanup.
        
        Args:
            cuit: CUIT identifier associated with the session
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        if cuit in self._sessions:
            # Remove session from dictionary
            del self._sessions[cuit]
            self.logger.info("session_deleted", cuit=cuit)
            return True
        
        # Session not found - nothing to delete
        return False
    
    async def is_valid(self, session: AFIPSession) -> bool:
        """Verify if a session is still valid.
        
        Checks both the session's internal validity flag and whether
        the session has expired based on the current time.
        
        Args:
            session: AFIPSession object to validate
            
        Returns:
            bool: True if session is valid and not expired, False otherwise
        """
        # First check the session's internal validity flag
        if not session.is_valid:
            return False
        
        # Check if session has expired by comparing with current time
        if datetime.now() >= session.expires_at:
            self.logger.warning("session_expired", cuit=session.cuit)
            return False
        
        # Session is valid and not expired
        return True


class EncryptedSessionStorage(ISessionStorage):
    """Encrypted session storage implementation for persistent storage.
    
    This storage backend provides secure, persistent storage for AFIP sessions
    by encrypting session data before writing to disk. It uses Fernet symmetric
    encryption (from the cryptography library) which provides authenticated
    encryption with associated data.
    
    Security features:
    - All session data is encrypted using Fernet (AES-128 in CBC mode)
    - Files are created with restrictive permissions (0o600)
    - Encryption keys are stored separately with restricted access
    - CUIT values are sanitized before use in filenames
    
    Attributes:
        storage_path: Path object pointing to the storage directory
        fernet: Fernet encryption instance
        logger: Structured logger instance with storage context
    """
    
    def __init__(self, storage_path: str, encryption_key: Optional[str] = None):
        """Initialize the encrypted storage backend.
        
        Creates the storage directory if it doesn't exist and sets up
        encryption. If no encryption key is provided, generates a new one
        and saves it securely.
        
        Args:
            storage_path: Directory path where encrypted sessions will be stored
            encryption_key: Optional encryption key (generated if not provided)
                           Can be string or bytes
        """
        self.storage_path = Path(storage_path)
        # Create storage directory with parent directories if needed
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Configure logger with storage type and path for debugging
        self.logger = logger.bind(storage="encrypted", path=str(self.storage_path))
        
        # Set up encryption - either use provided key or generate new one
        if encryption_key:
            # Handle both string and bytes encryption keys
            self.fernet = Fernet(
                encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            )
        else:
            # Generate a new encryption key for this storage instance
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            # Save the key securely for future use
            self._save_encryption_key(key)
    
    def _save_encryption_key(self, key: bytes) -> None:
        """Save the encryption key securely to disk.
        
        Writes the encryption key to a hidden file with restrictive permissions.
        The file is only readable/writable by the owner (0o600) to prevent
        unauthorized access to the encryption key.
        
        Args:
            key: Encryption key in bytes format
        """
        # Use hidden file (starts with .) for the encryption key
        key_path = self.storage_path / ".encryption_key"
        key_path.write_bytes(key)
        
        # Set restrictive permissions (read/write for owner only)
        # This prevents other users on the system from reading the key
        os.chmod(key_path, 0o600)
        
        self.logger.info("encryption_key_saved")
    
    def _get_session_path(self, cuit: str) -> Path:
        """Get the file path for a session.
        
        Constructs a safe filename from the CUIT by removing hyphens.
        This prevents potential security issues with special characters
        in filenames and ensures consistency.
        
        Args:
            cuit: CUIT identifier (may contain hyphens like "20-12345678-9")
            
        Returns:
            Path: Full path to the encrypted session file
        """
        # Remove hyphens from CUIT to create a safe filename
        # This prevents directory traversal attacks and filesystem issues
        safe_cuit = cuit.replace("-", "")
        
        # Use .enc extension to indicate encrypted content
        return self.storage_path / f"session_{safe_cuit}.enc"
    
    def _serialize_session(self, session: AFIPSession) -> Dict[str, Any]:
        """Serialize a session object to a JSON-compatible dictionary.
        
        Converts the AFIPSession object into a dictionary that can be
        JSON-serialized. Datetime objects are converted to ISO format
        strings for proper serialization and deserialization.
        
        Args:
            session: AFIPSession object to serialize
            
        Returns:
            Dict[str, Any]: Dictionary with session data ready for JSON serialization
        """
        return {
            "session_id": session.session_id,
            "cuit": session.cuit,
            "cookies": session.cookies,  # Cookie dict is already JSON-serializable
            "created_at": session.created_at.isoformat(),  # Convert to ISO string
            "expires_at": session.expires_at.isoformat(),  # Convert to ISO string
            "is_valid": session.is_valid
        }
    
    def _deserialize_session(self, data: Dict[str, Any]) -> AFIPSession:
        """Deserialize a dictionary back to an AFIPSession object.
        
        Reconstructs an AFIPSession object from the dictionary representation.
        ISO format datetime strings are converted back to datetime objects.
        
        Args:
            data: Dictionary containing serialized session data
            
        Returns:
            AFIPSession: Reconstructed session object
        """
        return AFIPSession(
            session_id=data["session_id"],
            cuit=data["cuit"],
            cookies=data["cookies"],
            # Convert ISO strings back to datetime objects
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            is_valid=data["is_valid"]
        )
    
    async def save(self, session: AFIPSession) -> bool:
        """Save an encrypted session to disk.
        
        Performs the following steps:
        1. Serializes the session to a JSON-compatible dictionary
        2. Converts to JSON string
        3. Encrypts the JSON data using Fernet encryption
        4. Writes encrypted data to disk with restrictive permissions
        
        The entire process is atomic - either all steps succeed or
        the operation fails without partial writes.
        
        Args:
            session: AFIPSession object to save
            
        Returns:
            bool: True if saved successfully, False on any error
        """
        try:
            # Step 1: Convert session object to dictionary
            session_data = self._serialize_session(session)
            
            # Step 2: Serialize to JSON string
            json_data = json.dumps(session_data)
            
            # Step 3: Encrypt the JSON string
            # Fernet handles encoding to bytes internally
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Step 4: Write encrypted data to disk
            session_path = self._get_session_path(session.cuit)
            session_path.write_bytes(encrypted_data)
            
            # Step 5: Set restrictive file permissions (owner read/write only)
            # This prevents other users from accessing encrypted session data
            os.chmod(session_path, 0o600)
            
            self.logger.info(
                "session_saved_encrypted",
                cuit=session.cuit,
                path=str(session_path)
            )
            return True
            
        except Exception as e:
            # Log full exception details for debugging
            self.logger.error(
                "session_save_error",
                error=str(e),
                exc_info=True  # Include full traceback
            )
            return False
    
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Load and decrypt a session from disk.
        
        Performs the reverse of the save operation:
        1. Checks if the session file exists
        2. Reads encrypted data from disk
        3. Decrypts the data using Fernet
        4. Deserializes JSON back to session object
        
        If any step fails (file not found, decryption error, corrupted data),
        returns None rather than raising an exception.
        
        Args:
            cuit: CUIT identifier for the session to load
            
        Returns:
            Optional[AFIPSession]: The loaded session or None if not found/error
        """
        try:
            # Get the expected file path for this CUIT
            session_path = self._get_session_path(cuit)
            
            # Check if session file exists
            if not session_path.exists():
                # Not an error - session might not exist yet
                self.logger.debug("session_file_not_found", cuit=cuit)
                return None
            
            # Read encrypted data from disk
            encrypted_data = session_path.read_bytes()
            
            # Decrypt the data - will raise if tampered or wrong key
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Parse JSON and reconstruct session object
            session_data = json.loads(decrypted_data.decode())
            session = self._deserialize_session(session_data)
            
            self.logger.info("session_loaded_decrypted", cuit=cuit)
            return session
            
        except Exception as e:
            # Could be decryption error, JSON parsing error, or file access error
            self.logger.error(
                "session_load_error",
                error=str(e),
                cuit=cuit,
                exc_info=True  # Include full traceback for debugging
            )
            return None
    
    async def delete(self, cuit: str) -> bool:
        """Delete an encrypted session from disk.
        
        Permanently removes the session file from disk. This operation
        is used for explicit logout or session cleanup.
        
        Args:
            cuit: CUIT identifier for the session to delete
            
        Returns:
            bool: True if file was deleted, False if not found or error
        """
        try:
            session_path = self._get_session_path(cuit)
            
            if session_path.exists():
                # Remove the file from disk
                session_path.unlink()
                self.logger.info("session_deleted", cuit=cuit)
                return True
            
            # File doesn't exist - nothing to delete
            return False
            
        except Exception as e:
            # Could be permission error or filesystem issue
            self.logger.error(
                "session_delete_error",
                error=str(e),
                cuit=cuit
            )
            return False
    
    async def is_valid(self, session: AFIPSession) -> bool:
        """Verify if a session is still valid.
        
        Performs two checks:
        1. Checks the session's internal validity flag
        2. Verifies the session hasn't expired
        
        If the session has expired, it automatically marks it as invalid
        and saves the updated state to disk. This ensures that expired
        sessions are properly marked for future checks.
        
        Args:
            session: AFIPSession object to validate
            
        Returns:
            bool: True if session is valid and not expired, False otherwise
        """
        # First check: internal validity flag
        if not session.is_valid:
            return False
        
        # Second check: expiration time
        if datetime.now() >= session.expires_at:
            self.logger.warning(
                "session_expired",
                cuit=session.cuit,
                expired_at=session.expires_at.isoformat()
            )
            
            # Mark session as invalid and persist the change
            # This prevents future attempts to use this expired session
            session.is_valid = False
            await self.save(session)
            
            return False
        
        # Session is valid and not expired
        return True