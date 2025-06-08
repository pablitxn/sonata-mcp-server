"""Integration tests for browser functionality."""
import pytest
from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig, BrowserType
from src.browser.engines.playwright_engine import PlaywrightEngine
from src.browser.engines.selenium_engine import SeleniumEngine


@pytest.mark.integration
class TestBrowserIntegration:
    """Integration tests for browser operations."""
    
    @pytest.fixture(autouse=True)
    def setup_factory(self):
        """Setup browser factory with engines."""
        BrowserEngineFactory.register_engine(BrowserType.PLAYWRIGHT, PlaywrightEngine)
        BrowserEngineFactory.register_engine(BrowserType.SELENIUM, SeleniumEngine)
        yield
        BrowserEngineFactory._engines.clear()
    
    @pytest.mark.asyncio
    async def test_playwright_navigation(self):
        """Test Playwright browser navigation."""
        config = BrowserConfig(
            headless=True,
            viewport={"width": 1920, "height": 1080}
        )
        
        engine = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
        
        try:
            context = await engine.create_context({})
            page = await context.new_page()
            
            await page.goto("https://example.com")
            content = await page.content()
            
            assert "Example Domain" in content
            
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_selenium_navigation(self):
        """Test Selenium browser navigation."""
        config = BrowserConfig(
            headless=True
        )
        
        engine = await BrowserEngineFactory.create(BrowserType.SELENIUM, config)
        
        try:
            context = await engine.create_context({})
            page = await context.new_page()
            
            await page.goto("https://example.com")
            content = await page.content()
            
            assert "Example Domain" in content
            
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_screenshot_capture(self):
        """Test screenshot functionality."""
        config = BrowserConfig(
            headless=True
        )
        
        engine = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
        
        try:
            context = await engine.create_context({})
            page = await context.new_page()
            
            await page.goto("https://example.com")
            screenshot = await page.screenshot()
            
            assert screenshot
            assert isinstance(screenshot, bytes)
            assert len(screenshot) > 0
            
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_javascript_execution(self):
        """Test JavaScript execution."""
        config = BrowserConfig(
            headless=True
        )
        
        engine = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
        
        try:
            context = await engine.create_context({})
            page = await context.new_page()
            
            await page.goto("https://example.com")
            
            # Execute JavaScript to get page title
            result = await page.evaluate("document.title")
            
            assert "Example Domain" in result
            
            # Execute JavaScript to modify DOM
            await page.evaluate(
                "document.querySelector('h1').textContent = 'Modified Title'"
            )
            
            # Verify modification
            new_title = await page.evaluate(
                "document.querySelector('h1').textContent"
            )
            
            assert new_title == "Modified Title"
            
        finally:
            await engine.cleanup()
    
    @pytest.mark.asyncio
    async def test_form_interaction(self, temp_test_server):
        """Test form filling and submission."""
        config = BrowserConfig(
            headless=True
        )
        
        engine = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
        
        try:
            context = await engine.create_context({})
            page = await context.new_page()
            
            await page.goto(f"{temp_test_server}/form.html")
            
            # Fill form fields
            await page.fill("#username", "testuser")
            await page.fill("#password", "testpass")
            
            # Verify form values were set before submission
            username_value = await page.evaluate(
                "document.getElementById('username').value"
            )
            password_value = await page.evaluate(
                "document.getElementById('password').value"
            )
            
            assert username_value == "testuser"
            assert password_value == "testpass"
            
            # Test that we can click the submit button (form submission test)
            await page.click("button[type='submit']")
            
            # The form will submit and page might reload, so we don't check values after
            
        finally:
            await engine.cleanup()