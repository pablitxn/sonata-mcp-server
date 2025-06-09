#!/usr/bin/env python3
"""Test script for AFIP login functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from browser.factory import BrowserEngineFactory
from browser.interfaces import BrowserConfig, BrowserType
from connectors.afip.connector import AFIPConnector
from connectors.afip.interfaces import AFIPCredentials, LoginStatus
from connectors.afip.session.storage import EncryptedSessionStorage


async def test_afip_login():
    """Test AFIP login with real credentials."""
    # Create browser factory
    browser_factory = BrowserEngineFactory()
    
    # Configure browser (headless mode)
    browser_config = BrowserConfig(
        headless=True,  # Run in headless mode
        viewport={"width": 1280, "height": 720}
    )
    
    # Create session storage
    session_storage = EncryptedSessionStorage("/tmp/afip_sessions")
    
    # Create AFIP connector
    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage,
        browser_config=browser_config
    )
    
    # Test credentials
    credentials = AFIPCredentials(
        cuit="43242",
        password="123123"
    )
    
    print(f"Testing AFIP login for CUIT: {credentials.cuit}")
    print("Starting browser automation...")
    
    try:
        # Attempt login
        status = await connector.login(credentials)
        
        print(f"\nLogin status: {status.value}")
        
        if status == LoginStatus.SUCCESS:
            print("✅ Login successful!")
            
            # Get session info
            session = await connector.get_session()
            if session:
                print(f"Session ID: {session.session_id}")
                print(f"Expires at: {session.expires_at}")
                
            # Try to get account statement
            print("\nAttempting to get account statement...")
            statement = await connector.get_account_statement()
            
            if statement:
                print(f"✅ Account statement retrieved!")
                print(f"Total debt: ${statement.total_debt}")
                print(f"Screenshot saved to: {statement.screenshot_path}")
            else:
                print("❌ Failed to get account statement")
                
        else:
            print(f"❌ Login failed with status: {status.value}")
            
    except Exception as e:
        print(f"❌ Error during login: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await connector.logout()


if __name__ == "__main__":
    print("AFIP Login Test Script")
    print("=" * 50)
    asyncio.run(test_afip_login())