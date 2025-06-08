import pytest
from unittest.mock import AsyncMock, MagicMock
from src.browser.protocols import BrowserConfig, BrowserResponse, PageScreenshot
from src.browser.interfaces import BrowserInterface


@pytest.fixture
def browser_config():
    """Default browser configuration for tests."""
    return BrowserConfig(
        browser_type="chromium",
        headless=True,
        args=["--no-sandbox", "--disable-gpu"]
    )


@pytest.fixture
def mock_browser_response():
    """Mock browser response object."""
    return BrowserResponse(
        url="https://example.com",
        title="Example Page",
        content="<html><body><h1>Welcome</h1><p>Test content</p></body></html>",
        status_code=200
    )


@pytest.fixture
def mock_screenshot():
    """Mock screenshot object."""
    return PageScreenshot(
        data=b"fake_screenshot_data",
        format="png"
    )


@pytest.fixture
def mock_browser_interface():
    """Mock browser interface for testing."""
    mock = AsyncMock(spec=BrowserInterface)
    
    # Setup default return values
    mock.navigate.return_value = BrowserResponse(
        url="https://example.com",
        title="Test Page",
        content="<html><body>Test</body></html>",
        status_code=200
    )
    mock.screenshot.return_value = PageScreenshot(
        data=b"screenshot_data",
        format="png"
    )
    mock.execute_script.return_value = {"result": "success"}
    
    return mock


@pytest.fixture
async def async_browser_interface():
    """Async browser interface fixture."""
    from src.browser.engines.playwright_engine import PlaywrightEngine
    
    engine = PlaywrightEngine()
    yield engine
    
    # Cleanup
    if engine._browser:
        await engine.close()


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
def mock_webdriver():
    """Mock Selenium WebDriver for testing."""
    driver = MagicMock()
    
    # Setup common properties
    driver.title = "Test Page"
    driver.current_url = "https://example.com"
    driver.page_source = "<html><body>Test</body></html>"
    
    # Setup methods
    driver.get_screenshot_as_png.return_value = b"screenshot_data"
    driver.execute_script.return_value = {"status": "ok"}
    
    # Mock find_element
    element = MagicMock()
    element.text = "Element text"
    element.get_attribute.return_value = "attribute_value"
    driver.find_element.return_value = element
    
    return driver


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page object."""
    page = AsyncMock()
    
    # Setup properties
    page.title.return_value = "Test Page"
    page.url = "https://example.com"
    page.content.return_value = "<html><body>Test</body></html>"
    
    # Setup methods
    page.screenshot.return_value = b"screenshot_data"
    page.evaluate.return_value = {"status": "ok"}
    
    # Mock selectors
    page.query_selector.return_value = AsyncMock()
    page.query_selector_all.return_value = [AsyncMock(), AsyncMock()]
    
    return page


@pytest.fixture
def browser_engine_config():
    """Configuration for different browser engines."""
    return {
        "playwright": {
            "chromium": {
                "headless": True,
                "args": ["--no-sandbox"]
            },
            "firefox": {
                "headless": True
            },
            "webkit": {
                "headless": True
            }
        },
        "selenium": {
            "chrome": {
                "headless": True,
                "args": ["--no-sandbox", "--disable-gpu"]
            },
            "firefox": {
                "headless": True
            },
            "edge": {
                "headless": True
            }
        }
    }