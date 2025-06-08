# tests/test_browser_interface.py
"""
Testing with mock implementations
"""
from abc import ABC

import pytest
from unittest.mock import AsyncMock

from src.browser.interfaces import IPage, IBrowserEngine


class MockPage(IPage, ABC):
    """Mock implementation for testing"""

    def __init__(self):
        self.visited_urls = []
        self.clicked_selectors = []

    async def goto(self, url: str, wait_until: str = "load") -> None:
        self.visited_urls.append(url)

    async def click(self, selector: str) -> None:
        self.clicked_selectors.append(selector)

    # ... implement other methods


@pytest.mark.asyncio
async def test_browser_interface():
    """Test that implementations follow the interface"""
    page = MockPage()

    # Should work with any IPage implementation
    await page.goto("https://example.com")
    await page.click("button#submit")

    assert "https://example.com" in page.visited_urls
    assert "button#submit" in page.clicked_selectors
