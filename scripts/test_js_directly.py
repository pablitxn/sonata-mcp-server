#!/usr/bin/env python3
"""Test JavaScript parsing directly in browser."""

import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


async def test_js():
    """Test JavaScript execution directly."""
    
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    
    try:
        # Load the saved HTML
        driver.get(f"file:///tmp/afip_account_page_after_calc.html")
        
        # Test the JavaScript
        result = driver.execute_script("""
            // Simple approach: Find all numbers matching the pattern and pick the right one
            const bodyText = document.body.innerText || '';
            
            // Find "Total Saldo Deudor" text
            const lines = bodyText.split('\\n');
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes('Total Saldo Deudor')) {
                    // Look at the next few lines for a number
                    for (let j = i; j < Math.min(i + 5, lines.length); j++) {
                        const line = lines[j].trim();
                        // Match number with comma thousand separator and period decimal
                        const match = line.match(/^([0-9]{1,3}(?:,[0-9]{3})*(?:\\.[0-9]{2}))$/);
                        if (match) {
                            return match[1];
                        }
                    }
                }
            }
            
            // Fallback: Find the first occurrence of the pattern after "Total Saldo Deudor"
            const deudorIndex = bodyText.indexOf('Total Saldo Deudor');
            if (deudorIndex > -1) {
                const textAfter = bodyText.substring(deudorIndex);
                const match = textAfter.match(/([0-9]{1,3}(?:,[0-9]{3})*(?:\\.[0-9]{2}))/);
                if (match) {
                    return match[1];
                }
            }
            
            return null;
        """)
        
        print(f"Result: {result}")
        
        # Also test what innerText returns
        text = driver.execute_script("return document.body.innerText")
        if "Total Saldo Deudor" in text:
            idx = text.index("Total Saldo Deudor")
            print(f"\nText around 'Total Saldo Deudor':")
            print(text[idx:idx+200])
            
    finally:
        driver.quit()


if __name__ == "__main__":
    asyncio.run(test_js())