"""Integration tests for browser functionality."""
import pytest
from src.browser.factory import BrowserFactory
from src.browser.protocols import BrowserConfig


@pytest.mark.integration
class TestBrowserIntegration:
    """Integration tests for browser operations."""
    
    @pytest.mark.asyncio
    async def test_playwright_navigation(self):
        """Test Playwright browser navigation."""
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            engine="playwright"
        )
        
        browser = await BrowserFactory.create(config)
        
        try:
            await browser.launch(config)
            response = await browser.navigate("https://example.com")
            
            assert response.url == "https://example.com"
            assert response.status_code == 200
            assert "Example Domain" in response.title
            
        finally:
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_selenium_navigation(self):
        """Test Selenium browser navigation."""
        config = BrowserConfig(
            browser_type="chrome",
            headless=True,
            engine="selenium"
        )
        
        browser = BrowserFactory.create(config)
        
        try:
            browser.launch(config)
            response = browser.navigate("https://example.com")
            
            assert response.url == "https://example.com"
            assert response.status_code == 200
            assert "Example Domain" in response.title
            
        finally:
            browser.close()
    
    @pytest.mark.asyncio
    async def test_screenshot_capture(self):
        """Test screenshot functionality."""
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            engine="playwright"
        )
        
        browser = await BrowserFactory.create(config)
        
        try:
            await browser.launch(config)
            await browser.navigate("https://example.com")
            
            screenshot = await browser.screenshot()
            
            assert screenshot.data
            assert screenshot.format == "png"
            assert len(screenshot.data) > 0
            
        finally:
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_javascript_execution(self):
        """Test JavaScript execution."""
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            engine="playwright"
        )
        
        browser = await BrowserFactory.create(config)
        
        try:
            await browser.launch(config)
            await browser.navigate("https://example.com")
            
            # Execute JavaScript to get page title
            result = await browser.execute_script("return document.title;")
            
            assert result == "Example Domain"
            
            # Execute JavaScript to modify DOM
            await browser.execute_script(
                "document.querySelector('h1').textContent = 'Modified Title';"
            )
            
            # Verify modification
            new_title = await browser.execute_script(
                "return document.querySelector('h1').textContent;"
            )
            
            assert new_title == "Modified Title"
            
        finally:
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_form_interaction(self, temp_test_server):
        """Test form filling and submission."""
        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            engine="playwright"
        )
        
        browser = await BrowserFactory.create(config)
        
        try:
            await browser.launch(config)
            await browser.navigate(f"{temp_test_server}/form.html")
            
            # Fill form fields
            await browser.fill("#username", "testuser")
            await browser.fill("#password", "testpass")
            
            # Submit form
            await browser.click("button[type='submit']")
            
            # Verify form values were set
            username_value = await browser.execute_script(
                "return document.getElementById('username').value;"
            )
            
            assert username_value == "testuser"
            
        finally:
            await browser.close()