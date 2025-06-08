import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from typing import Dict, List, Optional, Any
from src.browser.interfaces import BrowserConfig, BrowserType, IPage, IBrowserContext, IBrowserEngine


@pytest.fixture
def browser_config():
    """Default browser configuration for tests."""
    return BrowserConfig(
        headless=True,
        proxy=None,
        user_agent="Mozilla/5.0 (Test Browser)",
        viewport={"width": 1920, "height": 1080},
        extra_args=["--no-sandbox", "--disable-gpu"]
    )


@pytest.fixture
def mock_page():
    """Mock IPage implementation."""
    page = AsyncMock(spec=IPage)
    
    # Setup default return values
    page.goto.return_value = None
    page.wait_for_selector.return_value = None
    page.click.return_value = None
    page.fill.return_value = None
    page.evaluate.return_value = {"result": "success"}
    page.screenshot.return_value = b"fake_screenshot_data"
    page.content.return_value = "<html><body>Test content</body></html>"
    page.close.return_value = None
    
    return page


@pytest.fixture
def mock_browser_context():
    """Mock IBrowserContext implementation."""
    context = AsyncMock(spec=IBrowserContext)
    mock_page_instance = AsyncMock(spec=IPage)
    
    context.new_page.return_value = mock_page_instance
    context.close.return_value = None
    context.set_cookies.return_value = None
    context.get_cookies.return_value = []
    
    return context


@pytest.fixture
def mock_browser_engine():
    """Mock IBrowserEngine implementation."""
    engine = AsyncMock(spec=IBrowserEngine)
    mock_context = AsyncMock(spec=IBrowserContext)
    
    engine.initialize.return_value = None
    engine.create_context.return_value = mock_context
    engine.cleanup.return_value = None
    engine.is_initialized = True
    
    return engine


@pytest.fixture
def mock_playwright():
    """Mock Playwright objects."""
    with pytest.MonkeyPatch.context() as mp:
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Setup page methods
        mock_page.goto.return_value = None
        mock_page.title.return_value = "Test Page"
        mock_page.content.return_value = "<html><body>Test</body></html>"
        mock_page.screenshot.return_value = b"screenshot_data"
        mock_page.evaluate.return_value = {"status": "ok"}
        
        # Setup context
        mock_context.new_page.return_value = mock_page
        
        # Setup browser
        mock_browser.new_context.return_value = mock_context
        
        # Setup playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_playwright.firefox.launch.return_value = mock_browser
        mock_playwright.webkit.launch.return_value = mock_browser
        
        mp.setattr("playwright.async_api.async_playwright", lambda: mock_playwright)
        
        yield {
            'playwright': mock_playwright,
            'browser': mock_browser,
            'context': mock_context,
            'page': mock_page
        }


@pytest.fixture
def browser_test_pages():
    """HTML test pages for browser testing."""
    return {
        "login_form": """
        <html>
        <body>
            <form id="login-form">
                <input type="text" id="username" name="username" />
                <input type="password" id="password" name="password" />
                <button type="submit" id="submit">Login</button>
            </form>
        </body>
        </html>
        """,
        
        "captcha_page": """
        <html>
        <body>
            <div class="g-recaptcha" data-sitekey="test-key"></div>
            <form>
                <input type="text" name="data" />
                <button type="submit">Submit</button>
            </form>
        </body>
        </html>
        """,
        
        "search_results": """
        <html>
        <body>
            <div class="search-results">
                <div class="result">
                    <h3><a href="https://result1.com">Result 1</a></h3>
                    <p>Description of result 1</p>
                </div>
                <div class="result">
                    <h3><a href="https://result2.com">Result 2</a></h3>
                    <p>Description of result 2</p>
                </div>
            </div>
        </body>
        </html>
        """,
        
        "javascript_page": """
        <html>
        <head>
            <script>
                function getData() {
                    return {
                        timestamp: Date.now(),
                        userAgent: navigator.userAgent
                    };
                }
            </script>
        </head>
        <body>
            <div id="content">Initial content</div>
            <button onclick="document.getElementById('content').innerHTML = 'Updated'">
                Update
            </button>
        </body>
        </html>
        """
    }


@pytest.fixture
def mock_selenium_webdriver():
    """Mock Selenium WebDriver for testing."""
    with pytest.MonkeyPatch.context() as mp:
        mock_driver = MagicMock()
        mock_chrome_options = MagicMock()
        mock_firefox_options = MagicMock()
        
        # Setup driver properties
        mock_driver.title = "Test Page"
        mock_driver.current_url = "https://example.com"
        mock_driver.page_source = "<html><body>Test</body></html>"
        
        # Setup driver methods
        mock_driver.get.return_value = None
        mock_driver.find_element.return_value = MagicMock()
        mock_driver.execute_script.return_value = {"status": "ok"}
        mock_driver.save_screenshot.return_value = True
        mock_driver.quit.return_value = None
        
        # Mock element
        mock_element = MagicMock()
        mock_element.click.return_value = None
        mock_element.send_keys.return_value = None
        mock_element.clear.return_value = None
        mock_driver.find_element.return_value = mock_element
        
        # Setup options
        mock_chrome_options.add_argument.return_value = None
        mock_firefox_options.add_argument.return_value = None
        
        # Mock webdriver module
        mock_webdriver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver
        mock_webdriver.Firefox.return_value = mock_driver
        mock_webdriver.ChromeOptions.return_value = mock_chrome_options
        mock_webdriver.FirefoxOptions.return_value = mock_firefox_options
        
        mp.setattr("selenium.webdriver", mock_webdriver)
        
        yield {
            'webdriver': mock_webdriver,
            'driver': mock_driver,
            'chrome_options': mock_chrome_options,
            'firefox_options': mock_firefox_options,
            'element': mock_element
        }