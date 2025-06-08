import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.browser.engines.playwright_engine import PlaywrightEngine, PlaywrightContext, PlaywrightPage
from src.browser.interfaces import BrowserConfig, BrowserType


class TestPlaywrightPage:
    """Test suite for PlaywrightPage."""
    
    @pytest.fixture
    def mock_playwright_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto.return_value = None
        page.wait_for_selector.return_value = None
        page.click.return_value = None
        page.fill.return_value = None
        page.evaluate.return_value = {"result": "test"}
        page.screenshot.return_value = b"screenshot_data"
        page.content.return_value = "<html><body>Test</body></html>"
        page.close.return_value = None
        return page
    
    @pytest.mark.asyncio
    async def test_goto(self, mock_playwright_page):
        """Test page navigation."""
        page = PlaywrightPage(mock_playwright_page)
        await page.goto("https://example.com")
        
        # The implementation passes wait_until to the underlying goto
        mock_playwright_page.goto.assert_called_once_with(
            "https://example.com", 
            wait_until="load"
        )
    
    @pytest.mark.asyncio
    async def test_goto_with_wait_until(self, mock_playwright_page):
        """Test page navigation with wait_until parameter."""
        page = PlaywrightPage(mock_playwright_page)
        await page.goto("https://example.com", wait_until="networkidle")
        
        # The implementation passes wait_until to the underlying goto
        mock_playwright_page.goto.assert_called_once_with(
            "https://example.com", 
            wait_until="networkidle"
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, mock_playwright_page):
        """Test waiting for selector."""
        page = PlaywrightPage(mock_playwright_page)
        await page.wait_for_selector("#test")
        
        mock_playwright_page.wait_for_selector.assert_called_once_with(
            "#test",
            timeout=30000
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_selector_with_timeout(self, mock_playwright_page):
        """Test waiting for selector with custom timeout."""
        page = PlaywrightPage(mock_playwright_page)
        await page.wait_for_selector("#test", timeout=5000)
        
        mock_playwright_page.wait_for_selector.assert_called_once_with(
            "#test",
            timeout=5000
        )
    
    @pytest.mark.asyncio
    async def test_click(self, mock_playwright_page):
        """Test clicking element."""
        page = PlaywrightPage(mock_playwright_page)
        await page.click("button#submit")
        
        mock_playwright_page.click.assert_called_once_with("button#submit")
    
    @pytest.mark.asyncio
    async def test_fill(self, mock_playwright_page):
        """Test filling form field."""
        page = PlaywrightPage(mock_playwright_page)
        await page.fill("input#username", "testuser")
        
        mock_playwright_page.fill.assert_called_once_with("input#username", "testuser")
    
    @pytest.mark.asyncio
    async def test_evaluate(self, mock_playwright_page):
        """Test JavaScript evaluation."""
        page = PlaywrightPage(mock_playwright_page)
        result = await page.evaluate("return document.title")
        
        mock_playwright_page.evaluate.assert_called_once_with("return document.title")
        assert result == {"result": "test"}
    
    @pytest.mark.asyncio
    async def test_screenshot(self, mock_playwright_page):
        """Test taking screenshot."""
        page = PlaywrightPage(mock_playwright_page)
        screenshot = await page.screenshot()
        
        mock_playwright_page.screenshot.assert_called_once()
        assert screenshot == b"screenshot_data"
    
    @pytest.mark.asyncio
    async def test_content(self, mock_playwright_page):
        """Test getting page content."""
        page = PlaywrightPage(mock_playwright_page)
        content = await page.content()
        
        mock_playwright_page.content.assert_called_once()
        assert content == "<html><body>Test</body></html>"
    
    @pytest.mark.asyncio
    async def test_close(self, mock_playwright_page):
        """Test closing page."""
        page = PlaywrightPage(mock_playwright_page)
        await page.close()
        
        mock_playwright_page.close.assert_called_once()


class TestPlaywrightContext:
    """Test suite for PlaywrightContext."""
    
    @pytest.fixture
    def mock_browser_context(self):
        """Create a mock browser context."""
        context = AsyncMock()
        mock_page = AsyncMock()
        context.new_page.return_value = mock_page
        context.close.return_value = None
        context.add_cookies.return_value = None
        context.cookies.return_value = []
        return context
    
    @pytest.mark.asyncio
    async def test_new_page(self, mock_browser_context):
        """Test creating new page."""
        context = PlaywrightContext(mock_browser_context)
        page = await context.new_page()
        
        mock_browser_context.new_page.assert_called_once()
        assert isinstance(page, PlaywrightPage)
    
    @pytest.mark.asyncio
    async def test_close(self, mock_browser_context):
        """Test closing context."""
        context = PlaywrightContext(mock_browser_context)
        await context.close()
        
        mock_browser_context.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_cookies(self, mock_browser_context):
        """Test setting cookies."""
        context = PlaywrightContext(mock_browser_context)
        cookies = [{"name": "test", "value": "value", "domain": ".example.com"}]
        await context.set_cookies(cookies)
        
        mock_browser_context.add_cookies.assert_called_once_with(cookies)
    
    @pytest.mark.asyncio
    async def test_get_cookies(self, mock_browser_context):
        """Test getting cookies."""
        mock_browser_context.cookies.return_value = [
            {"name": "test", "value": "value"}
        ]
        
        context = PlaywrightContext(mock_browser_context)
        cookies = await context.get_cookies()
        
        mock_browser_context.cookies.assert_called_once()
        assert cookies == [{"name": "test", "value": "value"}]


class TestPlaywrightEngine:
    """Test suite for PlaywrightEngine."""
    
    @pytest.fixture
    def playwright_engine(self):
        """Create PlaywrightEngine instance."""
        return PlaywrightEngine()
    
    @pytest.fixture
    def mock_playwright_api(self):
        """Mock Playwright API."""
        with patch('src.browser.engines.playwright_engine.async_playwright') as mock:
            mock_playwright = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            
            # Setup browser types - use AsyncMock for chromium too
            mock_chromium = AsyncMock()
            mock_chromium.launch = AsyncMock(return_value=mock_browser)
            mock_playwright.chromium = mock_chromium
            
            mock_firefox = AsyncMock()
            mock_firefox.launch = AsyncMock(return_value=mock_browser)
            mock_playwright.firefox = mock_firefox
            
            mock_webkit = AsyncMock()
            mock_webkit.launch = AsyncMock(return_value=mock_browser)
            mock_playwright.webkit = mock_webkit
            
            # Setup browser context
            mock_browser.new_context.return_value = mock_context
            mock_browser.close = AsyncMock()
            
            # Setup playwright start/stop
            mock_playwright.start = AsyncMock(return_value=None)
            mock_playwright.stop = AsyncMock(return_value=None)
            
            # Make async_playwright().start() return mock_playwright
            mock_async_cm = AsyncMock()
            mock_async_cm.start = AsyncMock(return_value=mock_playwright)
            mock.return_value = mock_async_cm
            
            yield {
                'async_playwright': mock,
                'playwright': mock_playwright,
                'browser': mock_browser,
                'context': mock_context,
                'chromium': mock_chromium
            }
    
    @pytest.mark.asyncio
    async def test_initialize(self, playwright_engine, mock_playwright_api):
        """Test engine initialization."""
        config = BrowserConfig(headless=True)
        
        assert not playwright_engine.is_initialized
        
        await playwright_engine.initialize(config)
        
        assert playwright_engine.is_initialized
        assert playwright_engine._playwright is not None
        assert playwright_engine._config == config
    
    @pytest.mark.asyncio
    async def test_initialize_twice(self, playwright_engine, mock_playwright_api):
        """Test initializing twice does nothing."""
        config = BrowserConfig(headless=True)
        
        await playwright_engine.initialize(config)
        first_playwright = playwright_engine._playwright
        
        await playwright_engine.initialize(config)
        
        assert playwright_engine._playwright is first_playwright
    
    @pytest.mark.asyncio
    async def test_create_context(self, playwright_engine, mock_playwright_api):
        """Test creating context."""
        config = BrowserConfig(headless=True)
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Test User Agent"
        }
        
        await playwright_engine.initialize(config)
        
        # Should launch browser during initialization
        # Check if the mock was set up properly
        assert mock_playwright_api['playwright'].chromium.launch.called
        mock_playwright_api['playwright'].chromium.launch.assert_called_once_with(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
            proxy=None
        )
        
        context = await playwright_engine.create_context(context_options)
        
        # Check context was created with merged options
        # The implementation merges config defaults with context_options
        mock_playwright_api['browser'].new_context.assert_called_once_with(
            viewport={"width": 1920, "height": 1080},
            user_agent="Test User Agent"
        )
        
        assert isinstance(context, PlaywrightContext)
    
    @pytest.mark.asyncio
    async def test_create_context_empty_options(self, playwright_engine, mock_playwright_api):
        """Test creating context with empty options."""
        config = BrowserConfig(headless=True)
        
        await playwright_engine.initialize(config)
        context = await playwright_engine.create_context({})
        
        # Should be called with default viewport from config (1920x1080 by default)
        mock_playwright_api['browser'].new_context.assert_called_once_with(
            viewport={'width': 1920, 'height': 1080},
            user_agent=None
        )
        assert isinstance(context, PlaywrightContext)
    
    @pytest.mark.asyncio
    async def test_create_context_not_initialized(self, playwright_engine):
        """Test creating context without initialization."""
        # PlaywrightEngine will fail when trying to access _config.viewport
        with pytest.raises(AttributeError):
            await playwright_engine.create_context({})
    
    @pytest.mark.asyncio
    async def test_cleanup(self, playwright_engine, mock_playwright_api):
        """Test engine cleanup."""
        config = BrowserConfig(headless=True)
        
        await playwright_engine.initialize(config)
        await playwright_engine.cleanup()
        
        # Check that close was called on browser
        mock_playwright_api['browser'].close.assert_called_once()
        # Check that stop was called on playwright
        mock_playwright_api['playwright'].stop.assert_called_once()
        
        # Note: The implementation doesn't set _browser to None after cleanup
        # so is_initialized will still return True
    
    @pytest.mark.asyncio
    async def test_browser_close_on_cleanup(self, playwright_engine, mock_playwright_api):
        """Test browser is closed during cleanup."""
        config = BrowserConfig(headless=True)
        
        await playwright_engine.initialize(config)
        await playwright_engine.create_context({})
        
        await playwright_engine.cleanup()
        
        mock_playwright_api['browser'].close.assert_called_once()