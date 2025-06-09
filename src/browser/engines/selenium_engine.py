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
from selenium.webdriver.remote.webelement import WebElement

from config.mcp_logger import logger
from ..interfaces import IBrowserEngine, IBrowserContext, IPage, BrowserConfig


class SeleniumElement:
    """Wrapper for Selenium WebElement to match Playwright-like API"""
    
    def __init__(self, element: WebElement):
        self._element = element
        
    async def query_selector_all(self, selector: str) -> list['SeleniumElement']:
        """Find all child elements matching the selector"""
        loop = asyncio.get_event_loop()
        elements = await loop.run_in_executor(
            None,
            self._element.find_elements,
            By.CSS_SELECTOR,
            selector
        )
        return [SeleniumElement(el) for el in elements]
    
    async def inner_text(self) -> str:
        """Get the visible text of the element"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._element.text
        )
    
    async def click(self) -> None:
        """Click the element"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._element.click)


class SeleniumPage(IPage):
    """Selenium page wrapper - adapts sync to async"""

    def __init__(self, driver: webdriver.Chrome, window_handle: Optional[str] = None):
        self._driver = driver
        self._window_handle = window_handle
        
    async def _ensure_window_focus(self):
        """Ensure this page's window is focused"""
        if self._window_handle:
            loop = asyncio.get_event_loop()
            current = await loop.run_in_executor(
                None,
                lambda: self._driver.current_window_handle
            )
            if current != self._window_handle:
                await loop.run_in_executor(
                    None,
                    self._driver.switch_to.window,
                    self._window_handle
                )

    async def goto(self, url: str, wait_until: str = "load") -> None:
        await self._ensure_window_focus()
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._driver.get, url)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> Any:
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        wait = WebDriverWait(self._driver, timeout / 1000)
        element = await loop.run_in_executor(
            None,
            wait.until,
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return SeleniumElement(element)

    async def click(self, selector: str, timeout: int = 30000) -> None:
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        
        # Handle Playwright-style selectors
        if ':has-text(' in selector:
            # Convert button:has-text("text") to a Selenium-compatible approach
            import re
            match = re.match(r'(\w+):has-text\("([^"]+)"\)', selector)
            if match:
                tag, text = match.groups()
                elements = await loop.run_in_executor(
                    None,
                    self._driver.find_elements,
                    By.TAG_NAME,
                    tag
                )
                for elem in elements:
                    elem_text = await loop.run_in_executor(None, lambda: elem.text)
                    if text in elem_text:
                        await loop.run_in_executor(None, elem.click)
                        return
                raise Exception(f"Element with text '{text}' not found")
        
        # Standard CSS selector with timeout
        wait = WebDriverWait(self._driver, timeout / 1000)
        element = await loop.run_in_executor(
            None,
            wait.until,
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        await loop.run_in_executor(None, element.click)

    async def fill(self, selector: str, value: str) -> None:
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        element = self._driver.find_element(By.CSS_SELECTOR, selector)
        await loop.run_in_executor(None, element.clear)
        await loop.run_in_executor(None, element.send_keys, value)

    async def evaluate(self, script: str, *args) -> Any:
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        # If script is just a property access, wrap it in a return statement
        if not script.strip().startswith('return') and 'function' not in script:
            script = f"return {script}"
        
        # Convert SeleniumElement wrappers back to WebElement
        converted_args = []
        for arg in args:
            if isinstance(arg, SeleniumElement):
                converted_args.append(arg._element)
            else:
                converted_args.append(arg)
        
        return await loop.run_in_executor(
            None,
            self._driver.execute_script,
            script,
            *converted_args
        )

    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> bytes:
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        
        if full_page:
            # Selenium doesn't have built-in full page screenshot for all browsers
            # We'll take a regular screenshot for now
            # TODO: Implement full page screenshot with scrolling
            pass
        
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
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._driver.page_source
        )

    async def close(self) -> None:
        # Selenium doesn't have tab close, navigate to blank
        await self.goto("about:blank")
    
    async def query_selector_all(self, selector: str) -> list[SeleniumElement]:
        """Find all elements matching the selector"""
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        elements = await loop.run_in_executor(
            None,
            self._driver.find_elements,
            By.CSS_SELECTOR,
            selector
        )
        return [SeleniumElement(el) for el in elements]


class SeleniumContext(IBrowserContext):
    """Selenium context wrapper - simulates contexts with profiles"""

    def __init__(self, engine: 'SeleniumEngine', profile_dir: str):
        self._engine = engine
        self._profile_dir = profile_dir
        self._driver: Optional[webdriver.Chrome] = None

    async def new_page(self) -> IPage:
        loop = asyncio.get_event_loop()
        
        if not self._driver:
            # Create new driver instance
            options = self._engine._create_options()
            options.add_argument(f"user-data-dir={self._profile_dir}")

            self._driver = await loop.run_in_executor(
                None,
                lambda: webdriver.Chrome(options=options)
            )
            # Get the handle for the main window
            handle = await loop.run_in_executor(
                None,
                lambda: self._driver.current_window_handle
            )
            return SeleniumPage(self._driver, handle)
        else:
            # Open a new tab/window
            await loop.run_in_executor(
                None,
                self._driver.execute_script,
                "window.open('about:blank', '_blank');"
            )
            
            # Get all window handles and switch to the new one
            handles = await loop.run_in_executor(
                None,
                lambda: self._driver.window_handles
            )
            new_handle = handles[-1]  # The newest window
            
            await loop.run_in_executor(
                None,
                self._driver.switch_to.window,
                new_handle
            )
            
            return SeleniumPage(self._driver, new_handle)

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
    
    async def get_pages(self) -> list[IPage]:
        """Get all pages/tabs in the context"""
        if not self._driver:
            return []
        
        loop = asyncio.get_event_loop()
        
        # Get all window handles
        window_handles = await loop.run_in_executor(
            None,
            lambda: self._driver.window_handles
        )
        
        # Create a page wrapper for each window with its handle
        pages = []
        for handle in window_handles:
            pages.append(SeleniumPage(self._driver, handle))
        
        return pages


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
