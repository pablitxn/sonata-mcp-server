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

from src.config.mcp_logger import logger
from ..interfaces import IBrowserEngine, IBrowserContext, IPage, BrowserConfig


class SeleniumElement:
    """Wrapper for Selenium WebElement to match Playwright-like API"""
    
    def __init__(self, element: WebElement):
        self._element = element
        self.logger = logger.bind(component="selenium_element")
        
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
        self.logger.debug("selenium_element.click: clicking element")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._element.click)
        self.logger.debug("selenium_element.click: element clicked successfully")


class SeleniumPage(IPage):
    """Selenium page wrapper - adapts sync to async"""

    def __init__(self, driver: webdriver.Chrome, window_handle: Optional[str] = None):
        self._driver = driver
        self._window_handle = window_handle
        self.logger = logger.bind(component="selenium_page", window_handle=window_handle)
        
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
        self.logger.info("selenium_page.goto: navigating to URL", url=url, wait_until=wait_until)
        await self._ensure_window_focus()
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._driver.get, url)
        self.logger.info("selenium_page.goto: navigation complete", 
                        current_url=self._driver.current_url,
                        title=self._driver.title)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> Any:
        self.logger.info("selenium_page.wait_for_selector: waiting for selector", 
                        selector=selector, timeout_ms=timeout)
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        wait = WebDriverWait(self._driver, timeout / 1000)
        try:
            element = await loop.run_in_executor(
                None,
                wait.until,
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.logger.info("selenium_page.wait_for_selector: element found", selector=selector)
            return SeleniumElement(element)
        except Exception as e:
            self.logger.error("selenium_page.wait_for_selector: timeout waiting for selector",
                            selector=selector,
                            error=str(e),
                            current_url=self._driver.current_url)
            raise

    async def click(self, selector: str, timeout: int = 30000) -> None:
        self.logger.info("selenium_page.click: clicking element", selector=selector, timeout_ms=timeout)
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        
        # Handle Playwright-style selectors
        if ':has-text(' in selector:
            # Convert button:has-text("text") to a Selenium-compatible approach
            import re
            match = re.match(r'(\w+):has-text\("([^"]+)"\)', selector)
            if match:
                tag, text = match.groups()
                self.logger.debug("selenium_page.click: using has-text selector", tag=tag, text=text)
                elements = await loop.run_in_executor(
                    None,
                    self._driver.find_elements,
                    By.TAG_NAME,
                    tag
                )
                for i, elem in enumerate(elements):
                    elem_text = await loop.run_in_executor(None, lambda: elem.text)
                    if text in elem_text:
                        self.logger.info("selenium_page.click: found element with text", 
                                       index=i, elem_text=elem_text)
                        await loop.run_in_executor(None, elem.click)
                        self.logger.info("selenium_page.click: element clicked successfully")
                        return
                error_msg = f"Element with text '{text}' not found"
                self.logger.error("selenium_page.click: element not found", 
                                selector=selector, 
                                elements_checked=len(elements))
                raise Exception(error_msg)
        
        # Standard CSS selector with timeout
        try:
            wait = WebDriverWait(self._driver, timeout / 1000)
            element = await loop.run_in_executor(
                None,
                wait.until,
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            await loop.run_in_executor(None, element.click)
            self.logger.info("selenium_page.click: element clicked successfully", selector=selector)
        except Exception as e:
            self.logger.error("selenium_page.click: failed to click element",
                            selector=selector,
                            error=str(e),
                            current_url=self._driver.current_url)
            raise

    async def fill(self, selector: str, value: str) -> None:
        self.logger.info("selenium_page.fill: filling element", 
                        selector=selector, 
                        value_length=len(value),
                        value_masked=f"{value[:2]}...{value[-2:]}" if len(value) > 4 else "***")
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        try:
            element = self._driver.find_element(By.CSS_SELECTOR, selector)
            await loop.run_in_executor(None, element.clear)
            await loop.run_in_executor(None, element.send_keys, value)
            self.logger.info("selenium_page.fill: element filled successfully", selector=selector)
        except Exception as e:
            self.logger.error("selenium_page.fill: failed to fill element",
                            selector=selector,
                            error=str(e),
                            current_url=self._driver.current_url)
            raise

    async def evaluate(self, script: str, *args) -> Any:
        self.logger.debug("selenium_page.evaluate: executing JavaScript", 
                         script_preview=script[:100] + "..." if len(script) > 100 else script,
                         args_count=len(args))
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
        
        try:
            result = await loop.run_in_executor(
                None,
                self._driver.execute_script,
                script,
                *converted_args
            )
            self.logger.debug("selenium_page.evaluate: script executed successfully", 
                            result_type=type(result).__name__)
            return result
        except Exception as e:
            self.logger.error("selenium_page.evaluate: script execution failed",
                            error=str(e),
                            script_preview=script[:100],
                            current_url=self._driver.current_url)
            raise

    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> bytes:
        self.logger.info("selenium_page.screenshot: taking screenshot", 
                        path=path, 
                        full_page=full_page)
        await self._ensure_window_focus()
        loop = asyncio.get_event_loop()
        
        if full_page:
            # Selenium doesn't have built-in full page screenshot for all browsers
            # We'll take a regular screenshot for now
            # TODO: Implement full page screenshot with scrolling
            self.logger.warning("selenium_page.screenshot: full page screenshot not fully implemented")
        
        try:
            if path:
                await loop.run_in_executor(
                    None,
                    self._driver.save_screenshot,
                    path
                )
                self.logger.info("selenium_page.screenshot: screenshot saved", path=path)
            screenshot_data = await loop.run_in_executor(
                None,
                self._driver.get_screenshot_as_png
            )
            self.logger.info("selenium_page.screenshot: screenshot taken successfully", 
                           size_bytes=len(screenshot_data))
            return screenshot_data
        except Exception as e:
            self.logger.error("selenium_page.screenshot: failed to take screenshot",
                            error=str(e),
                            current_url=self._driver.current_url)
            raise

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
        self.logger = logger.bind(component="selenium_context", profile_dir=profile_dir)

    async def new_page(self) -> IPage:
        self.logger.info("selenium_context.new_page: creating new page")
        loop = asyncio.get_event_loop()
        
        if not self._driver:
            # Create new driver instance
            self.logger.info("selenium_context.new_page: initializing Chrome driver")
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
            self.logger.info("selenium_context.new_page: driver initialized", window_handle=handle)
            return SeleniumPage(self._driver, handle)
        else:
            # Open a new tab/window
            self.logger.info("selenium_context.new_page: opening new tab")
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
            
            self.logger.info("selenium_context.new_page: switching to new tab", 
                           window_handle=new_handle,
                           total_windows=len(handles))
            
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
            self.logger.info("selenium_context.set_cookies: setting cookies", count=len(cookies))
            loop = asyncio.get_event_loop()
            for i, cookie in enumerate(cookies):
                try:
                    await loop.run_in_executor(
                        None,
                        self._driver.add_cookie,
                        cookie
                    )
                    self.logger.debug("selenium_context.set_cookies: cookie set", 
                                    index=i,
                                    name=cookie.get('name'),
                                    domain=cookie.get('domain'))
                except Exception as e:
                    self.logger.warning("selenium_context.set_cookies: failed to set cookie",
                                      index=i,
                                      name=cookie.get('name'),
                                      error=str(e))

    async def get_cookies(self) -> list[Dict[str, Any]]:
        if self._driver:
            self.logger.info("selenium_context.get_cookies: retrieving cookies")
            loop = asyncio.get_event_loop()
            cookies = await loop.run_in_executor(
                None,
                self._driver.get_cookies
            )
            self.logger.info("selenium_context.get_cookies: cookies retrieved", count=len(cookies))
            return cookies
        self.logger.warning("selenium_context.get_cookies: no driver available")
        return []
    
    async def get_pages(self) -> list[IPage]:
        """Get all pages/tabs in the context"""
        if not self._driver:
            self.logger.warning("selenium_context.get_pages: no driver available")
            return []
        
        self.logger.info("selenium_context.get_pages: getting all pages")
        loop = asyncio.get_event_loop()
        
        # Get all window handles
        window_handles = await loop.run_in_executor(
            None,
            lambda: self._driver.window_handles
        )
        
        self.logger.info("selenium_context.get_pages: found windows", count=len(window_handles))
        
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
        self.logger = logger.bind(component="selenium_engine")

    async def initialize(self, config: BrowserConfig) -> None:
        self.logger.info("selenium_engine.initialize: initializing engine",
                        headless=config.headless,
                        viewport=config.viewport,
                        user_agent=config.user_agent)
        self._config = config
        self._initialized = True
        self.logger.info("selenium_engine.initialize: engine initialized successfully")

    def _create_options(self) -> Options:
        """Create Chrome options"""
        self.logger.debug("selenium_engine._create_options: creating Chrome options")
        options = Options()

        if self._config.headless:
            options.add_argument('--headless')
            self.logger.debug("selenium_engine._create_options: headless mode enabled")

        if self._config.user_agent:
            options.add_argument(f'user-agent={self._config.user_agent}')
            self.logger.debug("selenium_engine._create_options: custom user agent set")

        # Add standard args
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Add extra args
        for arg in self._config.extra_args:
            options.add_argument(arg)
            self.logger.debug("selenium_engine._create_options: added extra arg", arg=arg)

        return options

    async def create_context(self, context_options: Dict[str, Any]) -> IBrowserContext:
        # Simulate contexts with different profiles
        self._profile_counter += 1
        profile_dir = f"/tmp/selenium_profile_{self._profile_counter}"
        self.logger.info("selenium_engine.create_context: creating new context",
                        profile_dir=profile_dir,
                        context_options=context_options)
        return SeleniumContext(self, profile_dir)

    async def cleanup(self) -> None:
        self.logger.info("selenium_engine.cleanup: cleaning up engine")
        self.logger.info("selenium_engine.cleanup: engine cleaned up successfully")

    @property
    def is_initialized(self) -> bool:
        return self._initialized
