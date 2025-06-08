"""
Pytest configuration
"""
import pytest
import asyncio
from typing import AsyncGenerator

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def browser_engine():
    """Fixture for browser engine"""
    from src.browser.engine import BrowserEngine
    engine = BrowserEngine()
    await engine.initialize()
    yield engine
    await engine.cleanup()