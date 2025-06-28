"""
Base utilities for ATC Sports web automation.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging

logger = logging.getLogger(__name__)


class ATCSportsBase:
    """Base class for ATC Sports web automation."""
    
    BASE_URL = "https://atcsports.io"
    DEFAULT_TIMEOUT = 10
    
    def __init__(self, headless: bool = True):
        """Initialize the browser."""
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def start_browser(self):
        """Start the Chrome browser."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, self.DEFAULT_TIMEOUT)
        
        logger.info("Browser started successfully")
        
    def close_browser(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
            
    def navigate_to_home(self):
        """Navigate to ATC Sports homepage."""
        self.driver.get(self.BASE_URL)
        logger.info(f"Navigated to {self.BASE_URL}")
        
    def wait_for_element(self, locator, timeout=None):
        """Wait for an element to be present."""
        timeout = timeout or self.DEFAULT_TIMEOUT
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            logger.error(f"Element {locator} not found within {timeout} seconds")
            return None
            
    def wait_for_clickable(self, locator, timeout=None):
        """Wait for an element to be clickable."""
        timeout = timeout or self.DEFAULT_TIMEOUT
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            return element
        except TimeoutException:
            logger.error(f"Element {locator} not clickable within {timeout} seconds")
            return None
            
    def safe_click(self, locator, timeout=None):
        """Safely click an element."""
        element = self.wait_for_clickable(locator, timeout)
        if element:
            element.click()
            logger.info(f"Clicked element: {locator}")
            return True
        return False
        
    def safe_send_keys(self, locator, text, timeout=None):
        """Safely send keys to an element."""
        element = self.wait_for_element(locator, timeout)
        if element:
            element.clear()
            element.send_keys(text)
            logger.info(f"Sent keys to element: {locator}")
            return True
        return False
        
    def get_page_title(self):
        """Get the current page title."""
        return self.driver.title if self.driver else None
        
    def get_current_url(self):
        """Get the current URL."""
        return self.driver.current_url if self.driver else None
        
    def take_screenshot(self, filename):
        """Take a screenshot and save it."""
        if self.driver:
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved: {filename}")
            return True
        return False
        
    def scroll_to_element(self, locator):
        """Scroll to an element."""
        element = self.wait_for_element(locator)
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            logger.info(f"Scrolled to element: {locator}")
            return True
        return False
        
    def execute_script(self, script, *args):
        """Execute JavaScript."""
        if self.driver:
            return self.driver.execute_script(script, *args)
        return None
        
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()
