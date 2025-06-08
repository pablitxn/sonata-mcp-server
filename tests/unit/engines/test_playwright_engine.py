import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.browser.engines.playwright_engine import PlaywrightEngine
from src.browser.protocols import BrowserConfig, BrowserResponse, PageScreenshot


@pytest.fixture
async def playwright_engine():
    """Create a Playwright engine instance for testing."""
    engine = PlaywrightEngine()
    yield engine
    if engine._browser:
        await engine.close()


@pytest.fixture
def mock_playwright():
    """Mock Playwright objects."""
    with patch('src.browser.engines.playwright_engine.async_playwright') as mock:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        
        mock_page.title.return_value = "Test Page"
        mock_page.content.return_value = "<html><body>Test Content</body></html>"
        mock_page.url = "https://example.com"
        mock_page.screenshot.return_value = b"fake_screenshot_data"
        
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright_instance.firefox.launch.return_value = mock_browser
        mock_playwright_instance.webkit.launch.return_value = mock_browser
        
        mock.__aenter__.return_value = mock_playwright_instance
        
        yield {
            'playwright': mock,
            'instance': mock_playwright_instance,
            'browser': mock_browser,
            'context': mock_context,
            'page': mock_page
        }


class TestPlaywrightEngine:
    """Test suite for PlaywrightEngine."""
    
    async def test_initialization(self, playwright_engine):
        """Test engine initialization."""
        assert playwright_engine._browser is None
        assert playwright_engine._context is None
        assert playwright_engine._playwright is None
    
    async def test_launch_chromium(self, playwright_engine, mock_playwright):
        """Test launching Chromium browser."""
        config = BrowserConfig(browser_type="chromium", headless=True)
        await playwright_engine.launch(config)
        
        mock_playwright['instance'].chromium.launch.assert_called_once_with(
            headless=True,
            args=[]
        )
        assert playwright_engine._browser is not None
    
    async def test_launch_firefox(self, playwright_engine, mock_playwright):
        """Test launching Firefox browser."""
        config = BrowserConfig(browser_type="firefox", headless=False)
        await playwright_engine.launch(config)
        
        mock_playwright['instance'].firefox.launch.assert_called_once_with(
            headless=False,
            args=[]
        )
    
    async def test_launch_webkit(self, playwright_engine, mock_playwright):
        """Test launching WebKit browser."""
        config = BrowserConfig(browser_type="webkit", headless=True)
        await playwright_engine.launch(config)
        
        mock_playwright['instance'].webkit.launch.assert_called_once_with(
            headless=True,
            args=[]
        )
    
    async def test_launch_with_args(self, playwright_engine, mock_playwright):
        """Test launching browser with custom arguments."""
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        await playwright_engine.launch(config)
        
        mock_playwright['instance'].chromium.launch.assert_called_once_with(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
    
    async def test_navigate(self, playwright_engine, mock_playwright):
        """Test navigating to a URL."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        
        response = await playwright_engine.navigate("https://example.com")
        
        mock_playwright['page'].goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=30000
        )
        assert response.url == "https://example.com"
        assert response.title == "Test Page"
        assert response.content == "<html><body>Test Content</body></html>"
    
    async def test_navigate_with_timeout(self, playwright_engine, mock_playwright):
        """Test navigating with custom timeout."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        
        await playwright_engine.navigate("https://example.com", timeout=60)
        
        mock_playwright['page'].goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=60000
        )
    
    async def test_screenshot(self, playwright_engine, mock_playwright):
        """Test taking a screenshot."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        await playwright_engine.navigate("https://example.com")
        
        screenshot = await playwright_engine.screenshot()
        
        mock_playwright['page'].screenshot.assert_called_once_with(full_page=False)
        assert screenshot.data == b"fake_screenshot_data"
        assert screenshot.format == "png"
    
    async def test_screenshot_full_page(self, playwright_engine, mock_playwright):
        """Test taking a full page screenshot."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        await playwright_engine.navigate("https://example.com")
        
        screenshot = await playwright_engine.screenshot(full_page=True)
        
        mock_playwright['page'].screenshot.assert_called_once_with(full_page=True)
    
    async def test_execute_script(self, playwright_engine, mock_playwright):
        """Test executing JavaScript."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        await playwright_engine.navigate("https://example.com")
        
        mock_playwright['page'].evaluate.return_value = {"result": "test"}
        
        result = await playwright_engine.execute_script("return {result: 'test'}")
        
        mock_playwright['page'].evaluate.assert_called_once_with("return {result: 'test'}")
        assert result == {"result": "test"}
    
    async def test_click(self, playwright_engine, mock_playwright):
        """Test clicking an element."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        await playwright_engine.navigate("https://example.com")
        
        await playwright_engine.click("button#submit")
        
        mock_playwright['page'].click.assert_called_once_with("button#submit")
    
    async def test_fill(self, playwright_engine, mock_playwright):
        """Test filling a form field."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        await playwright_engine.navigate("https://example.com")
        
        await playwright_engine.fill("input#username", "testuser")
        
        mock_playwright['page'].fill.assert_called_once_with("input#username", "testuser")
    
    async def test_close(self, playwright_engine, mock_playwright):
        """Test closing the browser."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        
        await playwright_engine.close()
        
        mock_playwright['browser'].close.assert_called_once()
        assert playwright_engine._browser is None
        assert playwright_engine._context is None
    
    async def test_launch_without_close(self, mock_playwright):
        """Test that browser is launched only once."""
        engine = PlaywrightEngine()
        config = BrowserConfig(browser_type="chromium")
        
        await engine.launch(config)
        await engine.launch(config)  # Second launch should not create new browser
        
        mock_playwright['instance'].chromium.launch.assert_called_once()
    
    async def test_navigate_without_launch(self, playwright_engine):
        """Test navigating without launching browser first."""
        with pytest.raises(RuntimeError, match="Browser not launched"):
            await playwright_engine.navigate("https://example.com")
    
    async def test_screenshot_without_page(self, playwright_engine, mock_playwright):
        """Test taking screenshot without navigating first."""
        config = BrowserConfig(browser_type="chromium")
        await playwright_engine.launch(config)
        
        with pytest.raises(RuntimeError, match="No page loaded"):
            await playwright_engine.screenshot()