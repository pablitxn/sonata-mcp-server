# src/mcp_gov_connector/browser/interfaces.py
"""
Browser engine interfaces using ABC
Design Pattern: Strategy + Dependency Inversion Principle
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncContextManager
from dataclasses import dataclass
from enum import Enum


class BrowserType(Enum):
    """Supported browser types"""
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    PUPPETEER = "puppeteer"
    UNDETECTED_CHROME = "undetected"  # For anti-bot bypass


@dataclass
class BrowserConfig:
    """Browser configuration"""
    headless: bool = True
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = None
    extra_args: list[str] = None

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}
        if self.extra_args is None:
            self.extra_args = []


class IBrowserContext(ABC):
    """Interface for browser context"""

    @abstractmethod
    async def new_page(self) -> 'IPage':
        """Create a new page/tab"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the context"""
        pass

    @abstractmethod
    async def set_cookies(self, cookies: list[Dict[str, Any]]) -> None:
        """Set cookies for the context"""
        pass

    @abstractmethod
    async def get_cookies(self) -> list[Dict[str, Any]]:
        """Get all cookies"""
        pass


class IPage(ABC):
    """Interface for a browser page"""

    @abstractmethod
    async def goto(self, url: str, wait_until: str = "load") -> None:
        """Navigate to URL"""
        pass

    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """Wait for element to appear"""
        pass

    @abstractmethod
    async def click(self, selector: str) -> None:
        """Click an element"""
        pass

    @abstractmethod
    async def fill(self, selector: str, value: str) -> None:
        """Fill input field"""
        pass

    @abstractmethod
    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript"""
        pass

    @abstractmethod
    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Take screenshot"""
        pass

    @abstractmethod
    async def content(self) -> str:
        """Get page HTML content"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the page"""
        pass


class IBrowserEngine(ABC):
    """
    Abstract interface for browser engines
    Following Dependency Inversion Principle (SOLID)
    """

    @abstractmethod
    async def initialize(self, config: BrowserConfig) -> None:
        """Initialize the browser engine"""
        pass

    @abstractmethod
    async def create_context(self, context_options: Dict[str, Any]) -> IBrowserContext:
        """Create an isolated browser context"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup all resources"""
        pass

    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if engine is initialized"""
        pass
