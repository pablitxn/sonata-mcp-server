"""Debug AFIP login to see exact flow."""

import asyncio
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

load_dotenv()


def debug_afip_login():
    """Debug the AFIP login process step by step."""
    
    # Get credentials
    cuit = os.getenv("AFIP_CUIT", "20123456789")
    password = os.getenv("AFIP_PASSWORD", "password")
    
    print(f"CUIT: {cuit}")
    print(f"Password: {'*' * len(password)}")
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--headless')  # Comment out to see browser
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # Step 1: Navigate to AFIP
        print("\n1. Navigating to AFIP...")
        driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        time.sleep(3)
        
        # Step 2: Enter CUIT
        print("\n2. Looking for CUIT field...")
        cuit_field = wait.until(
            EC.presence_of_element_located((By.NAME, "F1:username"))
        )
        print("   ✓ Found CUIT field")
        
        cuit_field.clear()
        cuit_field.send_keys(cuit)
        print(f"   ✓ Entered CUIT: {cuit}")
        
        # Step 3: Click Next
        print("\n3. Looking for 'Siguiente' button...")
        next_button = driver.find_element(By.ID, "F1:btnSiguiente")
        print("   ✓ Found button")
        
        next_button.click()
        print("   ✓ Clicked 'Siguiente'")
        
        # Step 4: Wait for password field
        print("\n4. Waiting for password field...")
        time.sleep(3)  # Wait for page transition
        
        # Try different selectors for password
        password_selectors = [
            (By.NAME, "F1:password"),
            (By.ID, "F1:password"),
            (By.CSS_SELECTOR, 'input[type="password"]'),
            (By.CSS_SELECTOR, 'input[name*="password"]'),
            (By.CSS_SELECTOR, 'input[id*="password"]')
        ]
        
        password_field = None
        for by, selector in password_selectors:
            try:
                password_field = driver.find_element(by, selector)
                print(f"   ✓ Found password field with {by}: {selector}")
                break
            except:
                print(f"   ✗ Not found with {by}: {selector}")
        
        if password_field:
            password_field.clear()
            password_field.send_keys(password)
            print("   ✓ Entered password")
            
            # Step 5: Submit
            print("\n5. Looking for submit button...")
            submit_selectors = [
                (By.ID, "F1:btnIngresar"),
                (By.NAME, "F1:btnIngresar"),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.CSS_SELECTOR, 'input[value*="Ingresar"]')
            ]
            
            for by, selector in submit_selectors:
                try:
                    submit_btn = driver.find_element(by, selector)
                    print(f"   ✓ Found submit button with {by}: {selector}")
                    submit_btn.click()
                    break
                except:
                    print(f"   ✗ Not found with {by}: {selector}")
        else:
            print("   ✗ Password field not found!")
            
            # Debug: print all inputs on the page
            print("\n   Debug - All input fields on page:")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for i, inp in enumerate(inputs):
                inp_type = inp.get_attribute('type')
                inp_name = inp.get_attribute('name')
                inp_id = inp.get_attribute('id')
                if inp_type not in ['hidden', 'submit']:
                    print(f"     Input #{i}: type={inp_type}, name={inp_name}, id={inp_id}")
        
        # Step 6: Check result
        print("\n6. Waiting for login result...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"   Current URL: {current_url}")
        
        # Check for success indicators
        if "portal" in current_url or "inicio" in current_url:
            print("   ✓ Login successful!")
        else:
            print("   ✗ Login may have failed")
            
            # Check for error messages
            error_selectors = [
                (By.CLASS_NAME, "ui-messages-error"),
                (By.CLASS_NAME, "error"),
                (By.CSS_SELECTOR, '[class*="error"]'),
                (By.CSS_SELECTOR, '[class*="mensaje"]')
            ]
            
            for by, selector in error_selectors:
                try:
                    error = driver.find_element(by, selector)
                    print(f"   Error message: {error.text}")
                except:
                    pass
        
        # Take screenshot
        driver.save_screenshot("/tmp/afip_login_result.png")
        print("\n   Screenshot saved to: /tmp/afip_login_result.png")
        
        # Keep browser open
        print("\n   Keeping browser open for 30 seconds...")
        time.sleep(30)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        driver.save_screenshot("/tmp/afip_login_error.png")
        print("   Error screenshot saved to: /tmp/afip_login_error.png")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_afip_login()