"""Debug example for AFIP connector to identify login issues."""

import asyncio
import os
from datetime import datetime, timedelta

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig
from src.captcha.chain import CaptchaChain
from src.captcha.circuit_breaker import CircuitBreakerConfig
from src.captcha.solvers import CapSolverAI, TwoCaptchaSolver
from src.connectors.afip.connector import AFIPConnector
from src.connectors.afip.interfaces import AFIPCredentials, LoginStatus
from src.connectors.afip.session import EncryptedSessionStorage


async def debug_login_page():
    """Debug function to check AFIP login page structure."""
    
    # Configure the browser with visible window for debugging
    browser_config = BrowserConfig(
        headless=False,  # Keep browser visible to see what's happening
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    # Create browser factory
    browser_factory = BrowserEngineFactory()
    
    # Create a simple browser instance
    engine = browser_factory.create_engine("selenium", browser_config)
    browser = await engine.launch()
    context = await browser.new_context()
    page = await context.new_page()
    
    try:
        print("🔍 Navigating to AFIP login page...")
        await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        
        # Wait a bit for page to load
        await asyncio.sleep(3)
        
        print("\n📋 Checking for common login form selectors...")
        
        # List of possible selectors for username field
        possible_user_selectors = [
            'input[name="user"]',
            'input[name="username"]',
            'input[name="usuario"]',
            'input[name="cuit"]',
            'input[id="user"]',
            'input[id="username"]',
            'input[id="usuario"]',
            'input[id="cuit"]',
            'input[type="text"]',
            '#F1\\:username',  # Escaped colon for JSF-style IDs
            'input[placeholder*="CUIT"]',
            'input[placeholder*="Usuario"]'
        ]
        
        # List of possible selectors for password field
        possible_password_selectors = [
            'input[name="password"]',
            'input[name="clave"]',
            'input[name="pass"]',
            'input[id="password"]',
            'input[id="clave"]',
            'input[type="password"]',
            '#F1\\:password'
        ]
        
        # Try to find username field
        print("\n🔎 Looking for username/CUIT field...")
        username_field = None
        for selector in possible_user_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} element(s) with selector: {selector}")
                    username_field = selector
                    break
            except:
                pass
        
        if not username_field:
            print("❌ Could not find username field!")
        
        # Try to find password field
        print("\n🔎 Looking for password field...")
        password_field = None
        for selector in possible_password_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} element(s) with selector: {selector}")
                    password_field = selector
                    break
            except:
                pass
        
        if not password_field:
            print("❌ Could not find password field!")
        
        # Get page HTML to inspect structure
        print("\n📄 Getting page structure...")
        page_content = await page.content()
        
        # Look for forms
        forms = await page.query_selector_all('form')
        print(f"\n📝 Found {len(forms)} form(s) on the page")
        
        # Try to find all input fields
        all_inputs = await page.query_selector_all('input')
        print(f"\n🔤 Found {len(all_inputs)} input field(s) total")
        
        # Print details about each input
        for i, input_elem in enumerate(all_inputs[:10]):  # Limit to first 10
            try:
                input_type = await input_elem.get_attribute('type')
                input_name = await input_elem.get_attribute('name')
                input_id = await input_elem.get_attribute('id')
                input_placeholder = await input_elem.get_attribute('placeholder')
                
                print(f"\nInput #{i+1}:")
                print(f"  Type: {input_type}")
                print(f"  Name: {input_name}")
                print(f"  ID: {input_id}")
                print(f"  Placeholder: {input_placeholder}")
            except:
                pass
        
        # Save screenshot for inspection
        screenshot_path = "/tmp/afip_login_page.png"
        await page.screenshot(screenshot_path)
        print(f"\n📸 Screenshot saved to: {screenshot_path}")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"\n❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()
        print("\n✅ Debug session completed")


async def main_with_mock():
    """Main example using mock credentials (won't actually login)."""
    
    print("🚨 WARNING: This example uses mock credentials and won't actually login to AFIP")
    print("   It's designed to test the connector structure and error handling\n")
    
    # Configure the browser
    browser_config = BrowserConfig(
        headless=False,
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    # Create browser factory
    browser_factory = BrowserEngineFactory()
    
    # Configure session storage
    session_storage = EncryptedSessionStorage(
        storage_path="/tmp/afip_sessions",
        encryption_key=os.getenv("AFIP_SESSION_KEY")
    )
    
    # Configure captcha chain
    captcha_chain = CaptchaChain()
    
    # Create the connector
    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage,
        captcha_chain=captcha_chain,
        browser_config=browser_config
    )
    
    try:
        # Mock credentials
        credentials = AFIPCredentials(
            cuit="20-12345678-9",  # This is a mock CUIT
            password="mock_password"
        )
        
        print(f"🔐 Attempting login with mock CUIT: {credentials.cuit}")
        
        # This will fail but we can see how the error is handled
        login_status = await connector.login(credentials)
        
        print(f"\n📊 Login status: {login_status}")
        
    except Exception as e:
        print(f"\n❌ Expected error (using mock credentials): {e}")
    
    finally:
        await connector.logout()
        print("\n✅ Cleanup completed")


if __name__ == "__main__":
    print("AFIP Connector Debug Tool")
    print("========================\n")
    print("Choose an option:")
    print("1. Debug login page structure")
    print("2. Test connector with mock credentials")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(debug_login_page())
    elif choice == "2":
        asyncio.run(main_with_mock())
    else:
        print("Invalid choice!")