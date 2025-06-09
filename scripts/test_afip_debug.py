#!/usr/bin/env python3
"""Debug script to test AFIP account statement parsing."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


async def test_parsing():
    """Test the parsing of AFIP account statement HTML."""
    
    # Read the saved HTML
    html_path = "/tmp/afip_account_page_after_calc.html"
    if not os.path.exists(html_path):
        print("No saved HTML file found. Run test_afip_login.py with AFIP_DEBUG=true first.")
        return
    
    # Create a simple web driver to test JavaScript
    driver = webdriver.Chrome()
    
    try:
        # Load the HTML file
        driver.get(f"file://{html_path}")
        
        # Execute the JavaScript to find the debt value
        result = driver.execute_script("""
            // Find the cell containing "Total Saldo Deudor"
            const cells = document.querySelectorAll('td');
            const results = [];
            
            for (let i = 0; i < cells.length; i++) {
                const cellText = cells[i].innerText || cells[i].textContent || '';
                if (cellText.includes('Total Saldo Deudor')) {
                    results.push(`Found at index ${i}: ${cellText}`);
                    
                    // Check parent row
                    const row = cells[i].parentElement;
                    const rowHTML = row ? row.innerHTML.substring(0, 200) : 'No parent row';
                    results.push(`Parent row HTML: ${rowHTML}...`);
                    
                    // Check next 5 cells
                    for (let j = i + 1; j < cells.length && j < i + 6; j++) {
                        const nextCell = cells[j];
                        const text = (nextCell.innerText || nextCell.textContent || '').trim();
                        results.push(`Cell ${j}: "${text}"`);
                        
                        // Check for nested tables
                        const tables = nextCell.querySelectorAll('table');
                        if (tables.length > 0) {
                            results.push(`  - Contains ${tables.length} nested table(s)`);
                            tables.forEach((table, idx) => {
                                const tableText = (table.innerText || table.textContent || '').trim();
                                results.push(`    Table ${idx}: "${tableText}"`);
                            });
                        }
                    }
                    break;
                }
            }
            
            return results.join('\\n');
        """)
        
        print("JavaScript Debug Output:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        # Try a simpler approach
        result2 = driver.execute_script("""
            // Just look for the number pattern anywhere
            const text = document.body.innerText;
            const matches = text.match(/\\b\\d{1,3},\\d{3}\\.\\d{2}\\b/g);
            return matches ? matches : [];
        """)
        
        print("\nAll numbers matching pattern XXX,XXX.XX:")
        for num in result2:
            print(f"  - {num}")
            
    finally:
        driver.quit()


if __name__ == "__main__":
    asyncio.run(test_parsing())