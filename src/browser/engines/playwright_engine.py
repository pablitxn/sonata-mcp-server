"""
Playwright implementation of browser interfaces
"""
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import structlog

from ..interfaces import IBrowserEngine, IBrowserContext, IPage, BrowserConfig

logger = structlog.get_logger()


class PlaywrightPage(IPage):
    """Playwright page wrapper"""

    def __init__(self, page: Page):
        self._page = page

    async def goto(self, url: str, wait_until: str = "load") -> None:
        await self._page.goto(url, wait_until=wait_until)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        await self._page.wait_for_selector(selector, timeout=timeout)

    async def click(self, selector: str) -> None:
        await self._page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        await self._page.fill(selector, value)

    async def evaluate(self, script: str) -> Any:
        return await self._page.evaluate(script)

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        return await self._page.screenshot(path=path)

    async def content(self) -> str:
        return await self._page.content()

    async def close(self) -> None:
        await self._page.close()


class PlaywrightContext(IBrowserContext):
    """Playwright context wrapper"""

    def __init__(self, context: BrowserContext):
        self._context = context

    async def new_page(self) -> IPage:
        page = await self._context.new_page()
        return PlaywrightPage(page)

    async def close(self) -> None:
        await self._context.close()

    async def set_cookies(self, cookies: list[Dict[str, Any]]) -> None:
        await self._context.add_cookies(cookies)

    async def get_cookies(self) -> list[Dict[str, Any]]:
        return await self._context.cookies()


class PlaywrightEngine(IBrowserEngine):
    """
    Playwright browser engine implementation
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._config: Optional[BrowserConfig] = None

    async def initialize(self, config: BrowserConfig) -> None:
        """Initialize Playwright browser"""
        self._config = config
        self._playwright = await async_playwright().start()

        # Build launch arguments
        args = [
                   '--disable-blink-features=AutomationControlled',
                   '--no-sandbox',
                   '--disable-setuid-sandbox',
                   '--disable-dev-shm-usage',
               ] + config.extra_args

        self._browser = await self._playwright.chromium.launch(
            headless=config.headless,
            args=args,
            proxy={"server": config.proxy} if config.proxy else None
        )
        logger.info("Playwright engine initialized")

    async def create_context(self, context_options: Dict[str, Any]) -> IBrowserContext:
        """Create browser context with options"""
        options = {
            "viewport": self._config.viewport,
            "user_agent": self._config.user_agent,
            **context_options  # Allow override
        }

        context = await self._browser.new_context(**options)
        return PlaywrightContext(context)

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._browser:
            await self._browser.close()

        if self._playwright:
            await self._playwright.stop()

        logger.info("Playwright engine cleaned up")

    @property
    def is_initialized(self) -> bool:
        return self._browser is not None
