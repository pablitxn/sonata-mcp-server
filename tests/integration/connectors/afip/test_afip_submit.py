"""Test to find the submit button on AFIP login page."""

from selenium import webdriver
from selenium.webdriver.common.by import By
import time


def find_submit_button():
    """Find the submit button on AFIP login page."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        time.sleep(5)
        
        print("Looking for submit buttons...")
        
        # Find all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"\nFound {len(buttons)} button elements")
        
        for i, btn in enumerate(buttons):
            btn_type = btn.get_attribute('type')
            btn_id = btn.get_attribute('id')
            btn_text = btn.text
            btn_onclick = btn.get_attribute('onclick')
            
            print(f"\nButton #{i+1}:")
            print(f"  Type: {btn_type}")
            print(f"  ID: {btn_id}")
            print(f"  Text: {btn_text}")
            print(f"  OnClick: {btn_onclick}")
        
        # Find input elements with type submit
        submit_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')
        print(f"\nFound {len(submit_inputs)} input[type=submit] elements")
        
        for i, inp in enumerate(submit_inputs):
            inp_id = inp.get_attribute('id')
            inp_name = inp.get_attribute('name')
            inp_value = inp.get_attribute('value')
            
            print(f"\nSubmit Input #{i+1}:")
            print(f"  ID: {inp_id}")
            print(f"  Name: {inp_name}")
            print(f"  Value: {inp_value}")
        
        # Try specific selectors
        selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button[id*="btnIngresar"]',
            'input[id*="btnIngresar"]',
            '#F1\\:btnIngresar'
        ]
        
        print("\n\nTesting specific selectors:")
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✓ Found {len(elements)} element(s) with: {selector}")
            except:
                pass
        
    finally:
        driver.quit()


if __name__ == "__main__":
    find_submit_button()