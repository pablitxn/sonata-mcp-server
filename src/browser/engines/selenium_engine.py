"""
Selenium implementation of browser interfaces
"""
import asyncio
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import structlog

from ..interfaces import IBrowserEngine, IBrowserContext, IPage, BrowserConfig

logger = structlog.get_logger()


class SeleniumPage(IPage):
    """Selenium page wrapper - adapts sync to async"""

    def __init__(self, driver: webdriver.Chrome):
        self._driver = driver

    async def goto(self, url: str, wait_until: str = "load") -> None:
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._driver.get, url)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        loop = asyncio.get_event_loop()
        wait = WebDriverWait(self._driver, timeout / 1000)
        await loop.run_in_executor(
            None,
            wait.until,
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    async def click(self, selector: str) -> None:
        loop = asyncio.get_event_loop()
        element = self._driver.find_element(By.CSS_SELECTOR, selector)
        await loop.run_in_executor(None, element.click)

    async def fill(self, selector: str, value: str) -> None:
        loop = asyncio.get_event_loop()
        element = self._driver.find_element(By.CSS_SELECTOR, selector)
        await loop.run_in_executor(None, element.clear)
        await loop.run_in_executor(None, element.send_keys, value)

    async def evaluate(self, script: str) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._driver.execute_script,
            script
        )

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        loop = asyncio.get_event_loop()
        if path:
            await loop.run_in_executor(
                None,
                self._driver.save_screenshot,
                path
            )
        return await loop.run_in_executor(
            None,
            self._driver.get_screenshot_as_png
        )

    async def content(self) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.page_source
        )

    async def close(self) -> None:
        # Selenium doesn't have tab close, navigate to blank
        await self.goto("about:blank")


class SeleniumContext(IBrowserContext):
    """Selenium context wrapper - simulates contexts with profiles"""

    def __init__(self, engine: 'SeleniumEngine', profile_dir: str):
        self._engine = engine
        self._profile_dir = profile_dir
        self._driver: Optional[webdriver.Chrome] = None

    async def new_page(self) -> IPage:
        # Selenium doesn't support multiple pages per context
        # Create new driver instance
        loop = asyncio.get_event_loop()
        options = self._engine._create_options()
        options.add_argument(f"user-data-dir={self._profile_dir}")

        self._driver = await loop.run_in_executor(
            None,
            webdriver.Chrome,
            options=options
        )
        return SeleniumPage(self._driver)

    async def close(self) -> None:
        if self._driver:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._driver.quit)

    async def set_cookies(self, cookies: list[Dict[str, Any]]) -> None:
        if self._driver:
            loop = asyncio.get_event_loop()
            for cookie in cookies:
                await loop.run_in_executor(
                    None,
                    self._driver.add_cookie,
                    cookie
                )

    async def get_cookies(self) -> list[Dict[str, Any]]:
        if self._driver:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._driver.get_cookies
            )
        return []


class SeleniumEngine(IBrowserEngine):
    """Selenium browser engine implementation"""

    def __init__(self):
        self._config: Optional[BrowserConfig] = None
        self._initialized = False
        self._profile_counter = 0

    async def initialize(self, config: BrowserConfig) -> None:
        self._config = config
        self._initialized = True
        logger.info("Selenium engine initialized")

    def _create_options(self) -> Options:
        """Create Chrome options"""
        options = Options()

        if self._config.headless:
            options.add_argument('--headless')

        if self._config.user_agent:
            options.add_argument(f'user-agent={self._config.user_agent}')

        # Add standard args
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Add extra args
        for arg in self._config.extra_args:
            options.add_argument(arg)

        return options

    async def create_context(self, context_options: Dict[str, Any]) -> IBrowserContext:
        # Simulate contexts with different profiles
        self._profile_counter += 1
        profile_dir = f"/tmp/selenium_profile_{self._profile_counter}"
        return SeleniumContext(self, profile_dir)

    async def cleanup(self) -> None:
        logger.info("Selenium engine cleaned up")

    @property
    def is_initialized(self) -> bool:
        return self._initialized
