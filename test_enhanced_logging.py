#!/usr/bin/env python3
"""Test script to verify enhanced semantic logging in AFIP connector.

This script runs a simple test to demonstrate the new logging format.
Run with: python test_enhanced_logging.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from browser.factory import BrowserEngineFactory
from browser.interfaces import BrowserConfig, BrowserType
from connectors.afip.connector import AFIPConnector
from connectors.afip.interfaces import AFIPCredentials, LoginStatus
from connectors.afip.session.storage import InMemorySessionStorage
from config.mcp_logger import logger


async def test_logging():
    """Test the enhanced logging throughout the AFIP connector."""
    
    print("\n" + "="*80)
    print("AFIP CONNECTOR ENHANCED LOGGING TEST")
    print("="*80 + "\n")
    
    # Create test credentials (dummy values)
    test_cuit = "20-12345678-9"
    test_password = "test_password"
    
    try:
        # 1. Test browser factory logging
        print("1. Testing browser factory initialization...")
        browser_factory = BrowserEngineFactory()
        
        # 2. Test session storage logging  
        print("\n2. Testing session storage initialization...")
        session_storage = InMemorySessionStorage()
        
        # 3. Test browser config
        print("\n3. Setting up browser configuration...")
        browser_config = BrowserConfig(
            headless=True,
            viewport={"width": 1280, "height": 720}
        )
        
        # 4. Test connector initialization
        print("\n4. Creating AFIP connector...")
        connector = AFIPConnector(
            browser_factory=browser_factory,
            session_storage=session_storage,
            browser_config=browser_config
        )
        
        # 5. Test login attempt (will fail with test credentials)
        print("\n5. Testing login with dummy credentials...")
        print(f"   CUIT: {test_cuit}")
        print("   Note: This will fail as these are test credentials")
        
        credentials = AFIPCredentials(
            cuit=test_cuit,
            password=test_password
        )
        
        # This will fail but will demonstrate the logging
        status = await connector.login(credentials)
        print(f"\n   Login status: {status.value}")
        
    except Exception as e:
        print(f"\nExpected error occurred: {type(e).__name__}: {str(e)}")
        print("This is normal for test credentials.")
    
    print("\n" + "="*80)
    print("TEST COMPLETED - Check the logs above for semantic logging format")
    print("="*80 + "\n")
    
    print("Key logging patterns demonstrated:")
    print("- connector.<method>: <description>")
    print("- browser_factory.<method>: <description>")
    print("- memory_storage.<method>: <description>")
    print("- selenium_engine.<method>: <description>")
    print("- And more throughout the codebase")
    
    print("\nThe logs include:")
    print("- Method names and descriptions")
    print("- Input parameters (with sensitive data masked)")
    print("- Operation results")
    print("- Error details with types")
    print("- Contextual information for debugging")


if __name__ == "__main__":
    # Set environment variable for debug mode
    os.environ["AFIP_DEBUG"] = "true"
    
    # Run the test
    asyncio.run(test_logging())