"""Test script to check AFIP page selectors.

This script helps identify why the login is failing by checking
what selectors are actually present on the AFIP login page.
"""

import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def test_afip_page():
    """Test AFIP login page structure with Selenium."""
    
    print("🚀 Starting Selenium test...")
    
    # Create Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Run with GUI to see what's happening
    # options.add_argument('--headless')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("📍 Navigating to AFIP login page...")
        driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(5)
        
        print("\n🔍 Checking for input fields...")
        
        # Method 1: Find all input elements
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Found {len(inputs)} input elements total")
        
        # Print details about each input
        for i, input_elem in enumerate(inputs):
            try:
                input_type = input_elem.get_attribute('type')
                input_name = input_elem.get_attribute('name')
                input_id = input_elem.get_attribute('id')
                input_placeholder = input_elem.get_attribute('placeholder')
                
                if input_type in ['text', 'password', 'email']:
                    print(f"\n📝 Input #{i+1}:")
                    print(f"   Type: {input_type}")
                    print(f"   Name: {input_name}")
                    print(f"   ID: {input_id}")
                    print(f"   Placeholder: {input_placeholder}")
            except:
                pass
        
        # Method 2: Try specific selectors
        print("\n🎯 Testing specific selectors:")
        
        selectors_to_test = [
            ('input[name="user"]', 'By name="user"'),
            ('input[name="username"]', 'By name="username"'),
            ('input[name="F1:username"]', 'By name="F1:username"'),
            ('#F1\\:username', 'By ID F1:username'),
            ('input[type="text"]', 'Any text input'),
            ('input[type="password"]', 'Any password input'),
            ('input[placeholder*="CUIT"]', 'By placeholder containing CUIT'),
        ]
        
        for selector, description in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Found {len(elements)} element(s): {description}")
                else:
                    print(f"❌ Not found: {description}")
            except Exception as e:
                print(f"❌ Error testing {description}: {str(e)}")
        
        # Method 3: Check page source
        print("\n📄 Checking page source for clues...")
        page_source = driver.page_source
        
        # Look for form-related keywords
        keywords = ['user', 'username', 'cuit', 'password', 'login', 'F1:']
        for keyword in keywords:
            if keyword.lower() in page_source.lower():
                print(f"✓ Found '{keyword}' in page source")
        
        # Take screenshot
        print("\n📸 Taking screenshot...")
        driver.save_screenshot("/tmp/afip_test.png")
        print("Screenshot saved to: /tmp/afip_test.png")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Keeping browser open for 20 seconds...")
        print("You can manually inspect the page elements.")
        time.sleep(20)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🏁 Closing browser...")
        driver.quit()


if __name__ == "__main__":
    test_afip_page()