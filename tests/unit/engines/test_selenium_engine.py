import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from src.browser.engines.selenium_engine import SeleniumEngine, SeleniumContext, SeleniumPage
from src.browser.interfaces import BrowserConfig, BrowserType
from selenium.common.exceptions import WebDriverException


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
        driver.page_source = "<html><body>Test</body></html>"
        driver.quit.return_value = None
        return driver
    
    @pytest.fixture
    def selenium_page(self, mock_driver):
        """Create SeleniumPage instance."""
        return SeleniumPage(mock_driver)
    
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
        with patch('selenium.webdriver.support.wait.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            
            await selenium_page.wait_for_selector("#test")
            
            mock_wait.assert_called_once_with(mock_driver, 30)
            mock_wait_instance.until.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_selector_with_timeout(self, selenium_page, mock_driver):
        """Test waiting for selector with custom timeout."""
        with patch('selenium.webdriver.support.wait.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            
            await selenium_page.wait_for_selector("#test", timeout=5000)
            
            mock_wait.assert_called_once_with(mock_driver, 5)
            mock_wait_instance.until.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_click(self, selenium_page, mock_driver):
        """Test clicking element."""
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        
        await selenium_page.click("button#submit")
        
        mock_driver.find_element.assert_called_once_with("css selector", "button#submit")
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
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b"screenshot_data"
            mock_open.return_value.__enter__.return_value = mock_file
            
            screenshot = await selenium_page.screenshot()
            
            mock_driver.save_screenshot.assert_called_once()
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
        
        mock_driver.quit.assert_called_once()


class TestSeleniumContext:
    """Test suite for SeleniumContext."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock SeleniumEngine."""
        engine = MagicMock()
        engine._driver = MagicMock()
        return engine
    
    @pytest.fixture
    def selenium_context(self, mock_engine):
        """Create SeleniumContext instance."""
        return SeleniumContext(mock_engine, profile_dir="/tmp/test_profile")
    
    @pytest.mark.asyncio
    async def test_new_page(self, selenium_context, mock_engine):
        """Test creating new page (returns same driver)."""
        page = await selenium_context.new_page()
        
        assert isinstance(page, SeleniumPage)
        assert page._driver == mock_engine._driver
    
    @pytest.mark.asyncio
    async def test_close(self, selenium_context, mock_engine):
        """Test closing context."""
        await selenium_context.close()
        
        mock_engine._driver.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_cookies(self, selenium_context, mock_engine):
        """Test setting cookies."""
        cookies = [
            {"name": "test", "value": "value", "domain": ".example.com"}
        ]
        
        await selenium_context.set_cookies(cookies)
        
        mock_engine._driver.add_cookie.assert_called_once_with({
            "name": "test",
            "value": "value",
            "domain": ".example.com"
        })
    
    @pytest.mark.asyncio
    async def test_get_cookies(self, selenium_context, mock_engine):
        """Test getting cookies."""
        mock_engine._driver.get_cookies.return_value = [
            {"name": "test", "value": "value"}
        ]
        
        cookies = await selenium_context.get_cookies()
        
        mock_engine._driver.get_cookies.assert_called_once()
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
        with patch('src.browser.engines.selenium_engine.webdriver') as mock:
            mock_driver = MagicMock()
            mock_options = MagicMock()
            
            # Setup options
            mock.ChromeOptions.return_value = mock_options
            mock.FirefoxOptions.return_value = mock_options
            
            # Setup drivers
            mock.Chrome.return_value = mock_driver
            mock.Firefox.return_value = mock_driver
            
            yield {
                'webdriver': mock,
                'driver': mock_driver,
                'options': mock_options
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
        
        # Check options were set
        mock_webdriver['options'].add_argument.assert_any_call("--headless")
        mock_webdriver['options'].add_argument.assert_any_call("--no-sandbox")
        
        # Check driver was created
        mock_webdriver['webdriver'].Chrome.assert_called_once_with(
            options=mock_webdriver['options']
        )
        
        assert isinstance(context, SeleniumContext)
    
    @pytest.mark.asyncio
    async def test_create_context_with_user_agent(self, selenium_engine, mock_webdriver):
        """Test creating context with user agent in config."""
        config = BrowserConfig(
            headless=True,
            user_agent="Custom User Agent"
        )
        
        await selenium_engine.initialize(config)
        await selenium_engine.create_context({})
        
        mock_webdriver['options'].add_argument.assert_any_call(
            "--user-agent=Custom User Agent"
        )
    
    @pytest.mark.asyncio
    async def test_create_context_not_initialized(self, selenium_engine):
        """Test creating context without initialization."""
        with pytest.raises(RuntimeError, match="Engine not initialized"):
            await selenium_engine.create_context({})
    
    @pytest.mark.asyncio
    async def test_cleanup(self, selenium_engine, mock_webdriver):
        """Test engine cleanup."""
        config = BrowserConfig(headless=True)
        await selenium_engine.initialize(config)
        await selenium_engine.create_context({})
        
        await selenium_engine.cleanup()
        
        assert not selenium_engine.is_initialized
        mock_webdriver['driver'].quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, selenium_engine, mock_webdriver):
        """Test error handling in driver creation."""
        mock_webdriver['webdriver'].Chrome.side_effect = WebDriverException("Failed")
        
        config = BrowserConfig(headless=True)
        await selenium_engine.initialize(config)
        
        with pytest.raises(WebDriverException):
            await selenium_engine.create_context({})