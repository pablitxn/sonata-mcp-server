import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.browser.engines.selenium_engine import SeleniumEngine
from src.browser.protocols import BrowserConfig, BrowserResponse, PageScreenshot
from selenium.webdriver.support.wait import WebDriverWait


@pytest.fixture
def selenium_engine():
    """Create a Selenium engine instance for testing."""
    engine = SeleniumEngine()
    yield engine
    if engine._driver:
        engine.close()


@pytest.fixture
def mock_webdriver():
    """Mock Selenium WebDriver objects."""
    with patch('src.browser.engines.selenium_engine.webdriver') as mock_webdriver:
        mock_driver = MagicMock()
        mock_options = MagicMock()
        
        mock_driver.title = "Test Page"
        mock_driver.page_source = "<html><body>Test Content</body></html>"
        mock_driver.current_url = "https://example.com"
        mock_driver.get_screenshot_as_png.return_value = b"fake_screenshot_data"
        
        mock_webdriver.ChromeOptions.return_value = mock_options
        mock_webdriver.FirefoxOptions.return_value = mock_options
        mock_webdriver.EdgeOptions.return_value = mock_options
        
        mock_webdriver.Chrome.return_value = mock_driver
        mock_webdriver.Firefox.return_value = mock_driver
        mock_webdriver.Edge.return_value = mock_driver
        
        yield {
            'webdriver': mock_webdriver,
            'driver': mock_driver,
            'options': mock_options
        }


class TestSeleniumEngine:
    """Test suite for SeleniumEngine."""
    
    def test_initialization(self, selenium_engine):
        """Test engine initialization."""
        assert selenium_engine._driver is None
    
    def test_launch_chrome(self, selenium_engine, mock_webdriver):
        """Test launching Chrome browser."""
        config = BrowserConfig(browser_type="chrome", headless=True)
        selenium_engine.launch(config)
        
        mock_webdriver['options'].add_argument.assert_any_call("--headless")
        mock_webdriver['webdriver'].Chrome.assert_called_once_with(options=mock_webdriver['options'])
        assert selenium_engine._driver is not None
    
    def test_launch_firefox(self, selenium_engine, mock_webdriver):
        """Test launching Firefox browser."""
        config = BrowserConfig(browser_type="firefox", headless=False)
        selenium_engine.launch(config)
        
        mock_webdriver['webdriver'].Firefox.assert_called_once_with(options=mock_webdriver['options'])
    
    def test_launch_edge(self, selenium_engine, mock_webdriver):
        """Test launching Edge browser."""
        config = BrowserConfig(browser_type="edge", headless=True)
        selenium_engine.launch(config)
        
        mock_webdriver['options'].add_argument.assert_any_call("--headless")
        mock_webdriver['webdriver'].Edge.assert_called_once_with(options=mock_webdriver['options'])
    
    def test_launch_with_args(self, selenium_engine, mock_webdriver):
        """Test launching browser with custom arguments."""
        config = BrowserConfig(
            browser_type="chrome",
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        selenium_engine.launch(config)
        
        mock_webdriver['options'].add_argument.assert_any_call("--headless")
        mock_webdriver['options'].add_argument.assert_any_call("--no-sandbox")
        mock_webdriver['options'].add_argument.assert_any_call("--disable-gpu")
    
    def test_navigate(self, selenium_engine, mock_webdriver):
        """Test navigating to a URL."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        
        response = selenium_engine.navigate("https://example.com")
        
        mock_webdriver['driver'].get.assert_called_once_with("https://example.com")
        assert response.url == "https://example.com"
        assert response.title == "Test Page"
        assert response.content == "<html><body>Test Content</body></html>"
    
    def test_navigate_with_timeout(self, selenium_engine, mock_webdriver):
        """Test navigating with custom timeout."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        
        with patch.object(selenium_engine, '_wait_for_page_load') as mock_wait:
            selenium_engine.navigate("https://example.com", timeout=60)
            mock_wait.assert_called_once_with(60)
    
    def test_screenshot(self, selenium_engine, mock_webdriver):
        """Test taking a screenshot."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        selenium_engine.navigate("https://example.com")
        
        screenshot = selenium_engine.screenshot()
        
        mock_webdriver['driver'].get_screenshot_as_png.assert_called_once()
        assert screenshot.data == b"fake_screenshot_data"
        assert screenshot.format == "png"
    
    def test_screenshot_full_page(self, selenium_engine, mock_webdriver):
        """Test taking a full page screenshot (not directly supported by Selenium)."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        selenium_engine.navigate("https://example.com")
        
        screenshot = selenium_engine.screenshot(full_page=True)
        
        mock_webdriver['driver'].get_screenshot_as_png.assert_called_once()
    
    def test_execute_script(self, selenium_engine, mock_webdriver):
        """Test executing JavaScript."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        selenium_engine.navigate("https://example.com")
        
        mock_webdriver['driver'].execute_script.return_value = {"result": "test"}
        
        result = selenium_engine.execute_script("return {result: 'test'}")
        
        mock_webdriver['driver'].execute_script.assert_called_once_with("return {result: 'test'}")
        assert result == {"result": "test"}
    
    def test_click(self, selenium_engine, mock_webdriver):
        """Test clicking an element."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        selenium_engine.navigate("https://example.com")
        
        mock_element = MagicMock()
        mock_webdriver['driver'].find_element.return_value = mock_element
        
        selenium_engine.click("button#submit")
        
        mock_webdriver['driver'].find_element.assert_called_once_with("css selector", "button#submit")
        mock_element.click.assert_called_once()
    
    def test_fill(self, selenium_engine, mock_webdriver):
        """Test filling a form field."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        selenium_engine.navigate("https://example.com")
        
        mock_element = MagicMock()
        mock_webdriver['driver'].find_element.return_value = mock_element
        
        selenium_engine.fill("input#username", "testuser")
        
        mock_webdriver['driver'].find_element.assert_called_once_with("css selector", "input#username")
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("testuser")
    
    def test_close(self, selenium_engine, mock_webdriver):
        """Test closing the browser."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        
        selenium_engine.close()
        
        mock_webdriver['driver'].quit.assert_called_once()
        assert selenium_engine._driver is None
    
    def test_launch_without_close(self, mock_webdriver):
        """Test that browser is launched only once."""
        engine = SeleniumEngine()
        config = BrowserConfig(browser_type="chrome")
        
        engine.launch(config)
        engine.launch(config)  # Second launch should not create new browser
        
        mock_webdriver['webdriver'].Chrome.assert_called_once()
    
    def test_navigate_without_launch(self, selenium_engine):
        """Test navigating without launching browser first."""
        with pytest.raises(RuntimeError, match="Browser not launched"):
            selenium_engine.navigate("https://example.com")
    
    def test_screenshot_without_driver(self, selenium_engine):
        """Test taking screenshot without launching browser first."""
        with pytest.raises(RuntimeError, match="Browser not launched"):
            selenium_engine.screenshot()
    
    def test_wait_for_page_load(self, selenium_engine, mock_webdriver):
        """Test waiting for page to load."""
        config = BrowserConfig(browser_type="chrome")
        selenium_engine.launch(config)
        
        with patch('src.browser.engines.selenium_engine.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            
            selenium_engine._wait_for_page_load(30)
            
            mock_wait.assert_called_once_with(mock_webdriver['driver'], 30)
            mock_wait_instance.until.assert_called_once()
    
    def test_unsupported_browser_type(self, selenium_engine):
        """Test launching with unsupported browser type."""
        config = BrowserConfig(browser_type="safari")
        
        with pytest.raises(ValueError, match="Unsupported browser type"):
            selenium_engine.launch(config)