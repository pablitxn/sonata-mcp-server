"""Módulo de manejo de sesiones para AFIP."""

from .storage import EncryptedSessionStorage, InMemorySessionStorage

__all__ = ["EncryptedSessionStorage", "InMemorySessionStorage"]