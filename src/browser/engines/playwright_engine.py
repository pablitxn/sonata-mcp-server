"""
Playwright implementation of browser interfaces
"""
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config.mcp_logger import logger
from telemetry.factory import get_telemetry_provider
from telemetry.interfaces import ITelemetryProvider
from ..interfaces import IBrowserEngine, IBrowserContext, IPage, BrowserConfig


class PlaywrightPage(IPage):
    """Playwright page wrapper"""
    
    _telemetry: ITelemetryProvider = get_telemetry_provider()

    def __init__(self, page: Page):
        self._page = page
        self.logger = logger.bind(component="playwright_page")

    async def goto(self, url: str, wait_until: str = "load") -> None:
        with self._telemetry.timed_operation("browser_navigation", {"url": url, "wait_until": wait_until}):
            self.logger.info("playwright_page.goto: navigating to URL", url=url, wait_until=wait_until)
            try:
                await self._page.goto(url, wait_until=wait_until)
                self.logger.info("playwright_page.goto: navigation complete",
                               current_url=self._page.url,
                               title=await self._page.title())
            except Exception as e:
                self.logger.error("playwright_page.goto: navigation failed",
                                url=url,
                                error=str(e),
                                error_type=type(e).__name__)
                raise

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        self.logger.info("playwright_page.wait_for_selector: waiting for selector",
                        selector=selector, timeout_ms=timeout)
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            self.logger.info("playwright_page.wait_for_selector: element found", selector=selector)
        except Exception as e:
            self.logger.error("playwright_page.wait_for_selector: timeout waiting for selector",
                            selector=selector,
                            error=str(e),
                            current_url=self._page.url)
            raise

    async def click(self, selector: str) -> None:
        with self._telemetry.timed_operation("browser_click", {"selector": selector}):
            self.logger.info("playwright_page.click: clicking element", selector=selector)
            try:
                await self._page.click(selector)
                self.logger.info("playwright_page.click: element clicked successfully", selector=selector)
            except Exception as e:
                self.logger.error("playwright_page.click: failed to click element",
                                selector=selector,
                                error=str(e),
                                current_url=self._page.url)
                raise

    async def fill(self, selector: str, value: str) -> None:
        self.logger.info("playwright_page.fill: filling element",
                        selector=selector,
                        value_length=len(value),
                        value_masked=f"{value[:2]}...{value[-2:]}" if len(value) > 4 else "***")
        try:
            await self._page.fill(selector, value)
            self.logger.info("playwright_page.fill: element filled successfully", selector=selector)
        except Exception as e:
            self.logger.error("playwright_page.fill: failed to fill element",
                            selector=selector,
                            error=str(e),
                            current_url=self._page.url)
            raise

    async def evaluate(self, script: str) -> Any:
        self.logger.debug("playwright_page.evaluate: executing JavaScript",
                         script_preview=script[:100] + "..." if len(script) > 100 else script)
        try:
            result = await self._page.evaluate(script)
            self.logger.debug("playwright_page.evaluate: script executed successfully",
                            result_type=type(result).__name__)
            return result
        except Exception as e:
            self.logger.error("playwright_page.evaluate: script execution failed",
                            error=str(e),
                            script_preview=script[:100],
                            current_url=self._page.url)
            raise

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        self.logger.info("playwright_page.screenshot: taking screenshot", path=path)
        try:
            screenshot_data = await self._page.screenshot(path=path)
            self.logger.info("playwright_page.screenshot: screenshot taken successfully",
                           path=path,
                           size_bytes=len(screenshot_data) if isinstance(screenshot_data, bytes) else None)
            return screenshot_data
        except Exception as e:
            self.logger.error("playwright_page.screenshot: failed to take screenshot",
                            error=str(e),
                            current_url=self._page.url)
            raise

    async def content(self) -> str:
        return await self._page.content()

    async def close(self) -> None:
        await self._page.close()


class PlaywrightContext(IBrowserContext):
    """Playwright context wrapper"""

    def __init__(self, context: BrowserContext):
        self._context = context
        self.logger = logger.bind(component="playwright_context")

    async def new_page(self) -> IPage:
        self.logger.info("playwright_context.new_page: creating new page")
        try:
            page = await self._context.new_page()
            self.logger.info("playwright_context.new_page: page created successfully")
            return PlaywrightPage(page)
        except Exception as e:
            self.logger.error("playwright_context.new_page: failed to create page",
                            error=str(e))
            raise

    async def close(self) -> None:
        await self._context.close()

    async def set_cookies(self, cookies: list[Dict[str, Any]]) -> None:
        self.logger.info("playwright_context.set_cookies: setting cookies", count=len(cookies))
        try:
            await self._context.add_cookies(cookies)
            self.logger.info("playwright_context.set_cookies: cookies set successfully")
        except Exception as e:
            self.logger.error("playwright_context.set_cookies: failed to set cookies",
                            error=str(e),
                            count=len(cookies))
            raise

    async def get_cookies(self) -> list[Dict[str, Any]]:
        self.logger.info("playwright_context.get_cookies: retrieving cookies")
        try:
            cookies = await self._context.cookies()
            self.logger.info("playwright_context.get_cookies: cookies retrieved", count=len(cookies))
            return cookies
        except Exception as e:
            self.logger.error("playwright_context.get_cookies: failed to get cookies",
                            error=str(e))
            raise


class PlaywrightEngine(IBrowserEngine):
    """
    Playwright browser engine implementation
    """

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._config: Optional[BrowserConfig] = None
        self.logger = logger.bind(component="playwright_engine")

    async def initialize(self, config: BrowserConfig) -> None:
        """Initialize Playwright browser"""
        self.logger.info("playwright_engine.initialize: initializing engine",
                        headless=config.headless,
                        viewport=config.viewport,
                        user_agent=config.user_agent,
                        proxy=config.proxy)
        
        self._config = config
        self._playwright = await async_playwright().start()
        self.logger.debug("playwright_engine.initialize: playwright started")

        # Build launch arguments
        args = [
                   '--disable-blink-features=AutomationControlled',
                   '--no-sandbox',
                   '--disable-setuid-sandbox',
                   '--disable-dev-shm-usage',
               ] + config.extra_args
        
        self.logger.debug("playwright_engine.initialize: launching browser", args=args)

        self._browser = await self._playwright.chromium.launch(
            headless=config.headless,
            args=args,
            proxy={"server": config.proxy} if config.proxy else None
        )
        self.logger.info("playwright_engine.initialize: engine initialized successfully")

    async def create_context(self, context_options: Dict[str, Any]) -> IBrowserContext:
        """Create browser context with options"""
        options = {
            "viewport": self._config.viewport,
            "user_agent": self._config.user_agent,
            **context_options  # Allow override
        }
        
        self.logger.info("playwright_engine.create_context: creating new context",
                        options=options)
        
        try:
            context = await self._browser.new_context(**options)
            self.logger.info("playwright_engine.create_context: context created successfully")
            return PlaywrightContext(context)
        except Exception as e:
            self.logger.error("playwright_engine.create_context: failed to create context",
                            error=str(e),
                            options=options)
            raise

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("playwright_engine.cleanup: cleaning up engine")
        
        if self._browser:
            try:
                await self._browser.close()
                self.logger.debug("playwright_engine.cleanup: browser closed")
            except Exception as e:
                self.logger.warning("playwright_engine.cleanup: error closing browser",
                                  error=str(e))

        if self._playwright:
            try:
                await self._playwright.stop()
                self.logger.debug("playwright_engine.cleanup: playwright stopped")
            except Exception as e:
                self.logger.warning("playwright_engine.cleanup: error stopping playwright",
                                  error=str(e))

        self.logger.info("playwright_engine.cleanup: engine cleaned up successfully")

    @property
    def is_initialized(self) -> bool:
        return self._browser is not None
