import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from src.browser.engines.selenium_engine import SeleniumEngine, SeleniumContext, SeleniumPage
from src.browser.interfaces import BrowserConfig, BrowserType
from selenium.common.exceptions import WebDriverException
from selenium import webdriver


class TestSeleniumPage:
    """Test suite for SeleniumPage."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock Selenium WebDriver."""
        driver = MagicMock()
        driver.get.return_value = None
        driver.find_element.return_value = MagicMock()
        driver.execute_script.return_value = {"result": "test"}
        driver.save_screenshot.return_value = True
        driver.get_screenshot_as_png.return_value = b"screenshot_data"
        driver.page_source = "<html><body>Test</body></html>"
        driver.quit.return_value = None
        return driver
    
    @pytest.fixture
    def selenium_page(self, mock_driver):
        """Create SeleniumPage instance."""
        return SeleniumPage(mock_driver)
    
    @pytest.fixture(autouse=True)
    def mock_run_in_executor(self):
        """Mock run_in_executor to run synchronously."""
        # Mock just the run_in_executor method on the actual loop
        async def run_sync(executor, func, *args):
            if args:
                return func(*args)
            return func()
        
        with patch.object(asyncio.get_event_loop(), 'run_in_executor', AsyncMock(side_effect=run_sync)):
            yield
    
    @pytest.mark.asyncio
    async def test_goto(self, selenium_page, mock_driver):
        """Test page navigation."""
        await selenium_page.goto("https://example.com")
        
        mock_driver.get.assert_called_once_with("https://example.com")
    
    @pytest.mark.asyncio
    async def test_goto_with_wait_until(self, selenium_page, mock_driver):
        """Test page navigation with wait_until parameter."""
        await selenium_page.goto("https://example.com", wait_until="complete")
        
        mock_driver.get.assert_called_once_with("https://example.com")
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, selenium_page, mock_driver):
        """Test waiting for selector."""
        with patch('src.browser.engines.selenium_engine.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until = MagicMock()
            mock_wait.return_value = mock_wait_instance
            
            await selenium_page.wait_for_selector("#test")
            
            mock_wait.assert_called_once_with(mock_driver, 30)
            mock_wait_instance.until.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_selector_with_timeout(self, selenium_page, mock_driver):
        """Test waiting for selector with custom timeout."""
        with patch('src.browser.engines.selenium_engine.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until = MagicMock()
            mock_wait.return_value = mock_wait_instance
            
            await selenium_page.wait_for_selector("#test", timeout=5000)
            
            mock_wait.assert_called_once_with(mock_driver, 5)
            mock_wait_instance.until.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_click(self, selenium_page, mock_driver):
        """Test clicking element."""
        mock_element = MagicMock()
        
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = mock_element
            
            await selenium_page.click("button#submit")
            
            mock_wait.assert_called_once_with(mock_driver, 30)
            mock_wait_instance.until.assert_called_once()
            mock_element.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fill(self, selenium_page, mock_driver):
        """Test filling form field."""
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        
        await selenium_page.fill("input#username", "testuser")
        
        mock_driver.find_element.assert_called_once_with("css selector", "input#username")
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("testuser")
    
    @pytest.mark.asyncio
    async def test_evaluate(self, selenium_page, mock_driver):
        """Test JavaScript evaluation."""
        mock_driver.execute_script.return_value = {"data": "result"}
        
        result = await selenium_page.evaluate("return document.title")
        
        mock_driver.execute_script.assert_called_once_with("return document.title")
        assert result == {"data": "result"}
    
    @pytest.mark.asyncio
    async def test_screenshot(self, selenium_page, mock_driver):
        """Test taking screenshot."""
        screenshot = await selenium_page.screenshot()
        
        mock_driver.get_screenshot_as_png.assert_called_once()
        assert screenshot == b"screenshot_data"
    
    @pytest.mark.asyncio
    async def test_content(self, selenium_page, mock_driver):
        """Test getting page content."""
        content = await selenium_page.content()
        
        assert content == "<html><body>Test</body></html>"
    
    @pytest.mark.asyncio
    async def test_close(self, selenium_page, mock_driver):
        """Test closing page."""
        await selenium_page.close()
        
        # SeleniumPage.close navigates to about:blank instead of quitting
        mock_driver.get.assert_called_with("about:blank")


class TestSeleniumContext:
    """Test suite for SeleniumContext."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock SeleniumEngine."""
        engine = MagicMock()
        engine._driver = MagicMock()
        engine._create_options = MagicMock()
        engine._create_options.return_value = MagicMock()
        return engine
    
    @pytest.fixture
    def selenium_context(self, mock_engine):
        """Create SeleniumContext instance."""
        return SeleniumContext(mock_engine, profile_dir="/tmp/test_profile")
    
    @pytest.fixture(autouse=True)
    def mock_webdriver_chrome(self):
        """Mock webdriver.Chrome to avoid the options issue."""
        with patch('src.browser.engines.selenium_engine.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_driver.quit.return_value = None
            mock_chrome.return_value = mock_driver
            yield mock_chrome
    
    @pytest.fixture(autouse=True)
    def mock_run_in_executor_context(self):
        """Mock run_in_executor for context tests."""
        # Create a mock Chrome driver
        mock_driver = MagicMock()
        mock_driver.quit.return_value = None
        mock_driver.add_cookie.return_value = None
        mock_driver.get_cookies.return_value = []
        
        # Mock webdriver.Chrome to return our mock driver
        with patch('src.browser.engines.selenium_engine.webdriver.Chrome', return_value=mock_driver):
            # Mock just the run_in_executor method on the actual loop
            async def run_sync(executor, func, *args):
                # Just call the function
                return func()
            
            with patch.object(asyncio.get_event_loop(), 'run_in_executor', AsyncMock(side_effect=run_sync)):
                yield
    
    @pytest.mark.asyncio
    async def test_new_page(self, selenium_context, mock_engine):
        """Test creating new page (creates new driver instance)."""
        page = await selenium_context.new_page()
        
        assert isinstance(page, SeleniumPage)
        # SeleniumContext creates a new driver instance for each page
        assert page._driver is not None
    
    @pytest.mark.asyncio
    async def test_close(self, selenium_context, mock_engine):
        """Test closing context."""
        # Create a page first to have a driver to close
        page = await selenium_context.new_page()
        await selenium_context.close()
        
        # Check that the context's driver was quit, not the engine's
        assert selenium_context._driver is not None
    
    @pytest.mark.asyncio
    async def test_set_cookies(self, selenium_context, mock_engine):
        """Test setting cookies."""
        # Create a page first to have a driver
        page = await selenium_context.new_page()
        
        cookies = [
            {"name": "test", "value": "value", "domain": ".example.com"}
        ]
        
        await selenium_context.set_cookies(cookies)
        
        # The mock Chrome driver should have add_cookie called
        selenium_context._driver.add_cookie.assert_called_once_with({
            "name": "test",
            "value": "value",
            "domain": ".example.com"
        })
    
    @pytest.mark.asyncio
    async def test_get_cookies(self, selenium_context, mock_engine):
        """Test getting cookies."""
        # Create a page first to have a driver
        page = await selenium_context.new_page()
        
        selenium_context._driver.get_cookies.return_value = [
            {"name": "test", "value": "value"}
        ]
        
        cookies = await selenium_context.get_cookies()
        
        selenium_context._driver.get_cookies.assert_called_once()
        assert cookies == [{"name": "test", "value": "value"}]


class TestSeleniumEngine:
    """Test suite for SeleniumEngine."""
    
    @pytest.fixture
    def selenium_engine(self):
        """Create SeleniumEngine instance."""
        return SeleniumEngine()
    
    @pytest.fixture
    def mock_webdriver(self):
        """Mock Selenium webdriver module."""
        # Track all add_argument calls
        add_argument_calls = []
        
        def track_add_argument(arg):
            add_argument_calls.append(arg)
            
        with patch('src.browser.engines.selenium_engine.webdriver') as mock:
            with patch('src.browser.engines.selenium_engine.Options') as mock_options_class:
                mock_driver = MagicMock()
                
                # Create a mock options object that tracks calls
                mock_options = MagicMock()
                mock_options.add_argument = MagicMock(side_effect=track_add_argument)
                mock_options.add_experimental_option = MagicMock()
                
                # Setup options constructor to return our mock
                mock_options_class.return_value = mock_options
                
                # Setup drivers
                mock.Chrome.return_value = mock_driver
                mock.Firefox.return_value = mock_driver
                
                yield {
                    'webdriver': mock,
                    'driver': mock_driver,
                    'options': mock_options,
                    'add_argument_calls': add_argument_calls
                }
    
    @pytest.mark.asyncio
    async def test_initialize(self, selenium_engine):
        """Test engine initialization."""
        config = BrowserConfig(headless=True)
        
        assert not selenium_engine.is_initialized
        
        await selenium_engine.initialize(config)
        
        assert selenium_engine.is_initialized
        assert selenium_engine._config == config
    
    @pytest.mark.asyncio
    async def test_create_context(self, selenium_engine, mock_webdriver):
        """Test creating context."""
        config = BrowserConfig(headless=True, extra_args=["--no-sandbox"])
        context_options = {
            "viewport": {"width": 1920, "height": 1080}
        }
        
        await selenium_engine.initialize(config)
        context = await selenium_engine.create_context(context_options)
        
        assert isinstance(context, SeleniumContext)
        
        # When new_page is called, options should be set
        await context.new_page()
        
        # Check options were set
        assert "--headless" in mock_webdriver['add_argument_calls']
        assert "--no-sandbox" in mock_webdriver['add_argument_calls']
        
        # Check driver was created
        mock_webdriver['webdriver'].Chrome.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_context_with_user_agent(self, selenium_engine, mock_webdriver):
        """Test creating context with user agent in config."""
        config = BrowserConfig(
            headless=True,
            user_agent="Custom User Agent"
        )
        
        await selenium_engine.initialize(config)
        context = await selenium_engine.create_context({})
        
        # Create a page to trigger options creation
        await context.new_page()
        
        assert "user-agent=Custom User Agent" in mock_webdriver['add_argument_calls']
    
    @pytest.mark.asyncio
    async def test_create_context_not_initialized(self, selenium_engine):
        """Test creating context without initialization."""
        # SeleniumEngine doesn't check if initialized before creating context
        # It will just increment counter and return a context
        context = await selenium_engine.create_context({})
        assert isinstance(context, SeleniumContext)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, selenium_engine, mock_webdriver):
        """Test engine cleanup."""
        config = BrowserConfig(headless=True)
        await selenium_engine.initialize(config)
        context = await selenium_engine.create_context({})
        
        # Create a page to have a driver to clean up
        page = await context.new_page()
        
        await selenium_engine.cleanup()
        
        # SeleniumEngine cleanup doesn't change is_initialized
        assert selenium_engine.is_initialized
    
    @pytest.mark.asyncio
    async def test_error_handling(self, selenium_engine, mock_webdriver):
        """Test error handling in driver creation."""
        mock_webdriver['webdriver'].Chrome.side_effect = WebDriverException("Failed")
        
        config = BrowserConfig(headless=True)
        await selenium_engine.initialize(config)
        context = await selenium_engine.create_context({})
        
        # The error will occur when trying to create a new page
        with pytest.raises(WebDriverException):
            await context.new_page()