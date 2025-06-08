"""Simple test to verify Selenium is working correctly."""

import asyncio
from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig, BrowserType


async def test_selenium():
    """Test basic Selenium functionality."""
    
    print("Creating browser factory...")
    factory = BrowserEngineFactory()
    
    config = BrowserConfig(
        headless=False,
        viewport={"width": 1280, "height": 720}
    )
    
    print("Creating Selenium engine...")
    engine = await factory.create(BrowserType.SELENIUM, config)
    
    print("Creating context...")
    context = await engine.create_context({})
    
    print("Creating page...")
    page = await context.new_page()
    
    print("Navigating to AFIP...")
    await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
    
    print("Waiting 5 seconds...")
    await asyncio.sleep(5)
    
    print("Taking screenshot...")
    await page.screenshot("/tmp/selenium_test.png")
    
    print("Trying to find username field...")
    try:
        await page.wait_for_selector('input[name="F1:username"]', timeout=10000)
        print("✓ Found username field!")
    except Exception as e:
        print(f"✗ Could not find username field: {e}")
        
        # Try to get page content
        content = await page.content()
        print(f"Page content length: {len(content)}")
        
        # Save content for debugging
        with open("/tmp/afip_page.html", "w") as f:
            f.write(content)
        print("Page content saved to /tmp/afip_page.html")
    
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(test_selenium())