# tests/test_browser_interface.py
"""
Testing with mock implementations
"""
import pytest
from unittest.mock import AsyncMock

from src.browser.interfaces import IPage, IBrowserEngine


class MockPage(IPage):
    """Mock implementation for testing"""

    def __init__(self):
        self.visited_urls = []
        self.clicked_selectors = []

    async def goto(self, url: str, wait_until: str = "load") -> None:
        self.visited_urls.append(url)

    async def click(self, selector: str) -> None:
        self.clicked_selectors.append(selector)
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        pass
    
    async def fill(self, selector: str, value: str) -> None:
        pass
    
    async def evaluate(self, script: str) -> any:
        return {"result": "mock"}
    
    async def screenshot(self) -> bytes:
        return b"mock_screenshot"
    
    async def content(self) -> str:
        return "<html><body>Mock content</body></html>"
    
    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_browser_interface():
    """Test that implementations follow the interface"""
    page = MockPage()

    # Should work with any IPage implementation
    await page.goto("https://example.com")
    await page.click("button#submit")

    assert "https://example.com" in page.visited_urls
    assert "button#submit" in page.clicked_selectors
