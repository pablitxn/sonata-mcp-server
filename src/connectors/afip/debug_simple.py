"""Simple debug script to check AFIP login page."""

import asyncio
from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig


async def check_afip_page():
    """Check AFIP login page structure."""
    
    browser_config = BrowserConfig(
        headless=True,  # Run headless for CI
        viewport={"width": 1280, "height": 720}
    )
    
    browser_factory = BrowserEngineFactory()
    engine = browser_factory.create_engine("selenium", browser_config)
    browser = await engine.launch()
    context = await browser.new_context()
    page = await context.new_page()
    
    try:
        print("Navigating to AFIP...")
        await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        await asyncio.sleep(5)  # Wait for page to load
        
        # Check what inputs exist
        inputs = await page.query_selector_all('input')
        print(f"\nFound {len(inputs)} input fields")
        
        # Check specific selectors
        selectors = [
            'input[name="user"]',
            'input[name="F1:username"]',
            '#F1\\:username',
            'input[type="text"]'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"✓ Found: {selector}")
                else:
                    print(f"✗ Not found: {selector}")
            except Exception as e:
                print(f"✗ Error checking {selector}: {e}")
        
        # Take screenshot
        await page.screenshot("/tmp/afip_debug.png")
        print("\nScreenshot saved to /tmp/afip_debug.png")
        
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(check_afip_page())