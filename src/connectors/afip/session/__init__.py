"""Session management module for AFIP.

This module provides session storage implementations for persisting AFIP authentication sessions.
Session persistence allows users to maintain their login state across application restarts,
avoiding repeated authentication and captcha solving.

Available implementations:
- EncryptedSessionStorage: Production-ready storage with encryption for sensitive data
- InMemorySessionStorage: Simple in-memory storage for testing and development
"""

# Import storage implementations
from .storage import EncryptedSessionStorage, InMemorySessionStorage

# Public API exports
__all__ = ["EncryptedSessionStorage", "InMemorySessionStorage"]