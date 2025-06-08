"""Test to find all input fields on AFIP login page."""

from selenium import webdriver
from selenium.webdriver.common.by import By
import time


def find_all_fields():
    """Find all form fields on AFIP login page."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        time.sleep(5)
        
        print("Looking for all input fields with name attribute...")
        
        # Find all inputs with name attribute
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[name]')
        print(f"\nFound {len(inputs)} input elements with name attribute")
        
        for i, inp in enumerate(inputs):
            inp_type = inp.get_attribute('type')
            inp_name = inp.get_attribute('name')
            inp_id = inp.get_attribute('id')
            
            print(f"\nInput #{i+1}:")
            print(f"  Type: {inp_type}")
            print(f"  Name: {inp_name}")
            print(f"  ID: {inp_id}")
            
            # Highlight the field to see it visually
            driver.execute_script("arguments[0].style.border='3px solid red'", inp)
        
        # Check if second page is needed
        print("\n\nNow clicking 'Siguiente' to see if password field is on next page...")
        
        # Fill username first
        username_field = driver.find_element(By.NAME, "F1:username")
        username_field.send_keys("20-12345678-9")
        
        # Click submit
        submit_btn = driver.find_element(By.ID, "F1:btnSiguiente")
        submit_btn.click()
        
        time.sleep(3)
        
        print("\nAfter clicking 'Siguiente'...")
        
        # Find all inputs again
        inputs_page2 = driver.find_elements(By.CSS_SELECTOR, 'input[name]')
        print(f"\nFound {len(inputs_page2)} input elements on second page")
        
        for i, inp in enumerate(inputs_page2):
            inp_type = inp.get_attribute('type')
            inp_name = inp.get_attribute('name')
            inp_id = inp.get_attribute('id')
            
            print(f"\nInput #{i+1}:")
            print(f"  Type: {inp_type}")
            print(f"  Name: {inp_name}")
            print(f"  ID: {inp_id}")
        
        time.sleep(10)  # Keep browser open to see
        
    finally:
        driver.quit()


if __name__ == "__main__":
    find_all_fields()