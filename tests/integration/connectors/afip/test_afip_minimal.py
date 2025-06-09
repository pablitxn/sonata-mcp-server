"""Minimal AFIP login test to isolate the issue."""

import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig, BrowserType
from src.connectors.afip.interfaces import AFIPCredentials, AFIPSession, LoginStatus
from src.connectors.afip.session import EncryptedSessionStorage


async def minimal_afip_login():
    """Minimal AFIP login implementation."""
    
    # Setup
    factory = BrowserEngineFactory()
    config = BrowserConfig(headless=False)
    
    # Create browser
    print("1. Creating browser...")
    engine = await factory.create(BrowserType.SELENIUM, config)
    context = await engine.create_context({})
    page = await context.new_page()
    
    # Navigate
    print("2. Navigating to AFIP...")
    await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
    await asyncio.sleep(3)
    
    # Enter CUIT
    print("3. Entering CUIT...")
    cuit = os.getenv("AFIP_CUIT", "2131231231")
    try:
        await page.wait_for_selector('input[name="F1:username"]', timeout=10000)
        await page.fill('input[name="F1:username"]', cuit)
        print(f"   ✓ Entered CUIT: {cuit}")
    except Exception as e:
        print(f"   ✗ Error entering CUIT: {e}")
        return
    
    # Click next
    print("4. Clicking 'Siguiente'...")
    await page.click('input[id="F1:btnSiguiente"]')
    await asyncio.sleep(2)
    
    # Enter password
    print("5. Entering password...")
    password = os.getenv("AFIP_PASSWORD", "password")
    try:
        await page.wait_for_selector('input[name="F1:password"]', timeout=10000)
        await page.fill('input[name="F1:password"]', password)
        print("   ✓ Entered password")
    except Exception as e:
        print(f"   ✗ Error entering password: {e}")
        return
    
    # Submit
    print("6. Clicking 'Ingresar'...")
    await page.click('input[id="F1:btnIngresar"]')
    await asyncio.sleep(5)
    
    # Check result
    print("7. Checking result...")
    current_url = await page.evaluate("window.location.href")
    print(f"   Current URL: {current_url}")
    
    if current_url and "portalcf.cloud.afip.gob.ar/portal/app" in current_url:
        print("   ✓ Login successful!")
        
        # Save session
        print("8. Saving session...")
        storage = EncryptedSessionStorage("/tmp/afip_sessions")
        cookies = await context.get_cookies()
        
        session = AFIPSession(
            session_id=f"afip_{cuit}_{datetime.now().timestamp()}",
            cuit=cuit,
            cookies={c["name"]: c["value"] for c in cookies},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=True
        )
        
        await storage.save(session)
        print("   ✓ Session saved!")
    else:
        print("   ✗ Login failed")
    
    # Cleanup
    await asyncio.sleep(10)  # Keep browser open to see result
    print("\nClosing browser...")


if __name__ == "__main__":
    asyncio.run(minimal_afip_login())