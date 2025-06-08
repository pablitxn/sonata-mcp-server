from mcp.server.fastmcp import FastMCP, Context
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def register_google_search_tool(mcp: FastMCP):
    """Register Google search tool with the MCP server."""
    
    @mcp.tool()
    async def search_google_today(ctx: Context) -> str:
        """Navigate to Google, search for 'que dia es hoy' and return the results.
        
        This tool uses Selenium to perform a Google search for 'what day is today' in Spanish
        and returns the search results.
        
        Args:
            ctx: The MCP server provided context
            
        Returns:
            str: The search results or error message
        """
        driver = None
        try:
            # Configure Chrome options for faster execution
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources
            
            # Create browser instance with implicit wait
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(5)  # Set implicit wait
            
            # Navigate to Google
            driver.get("https://www.google.com")
            
            # Wait for search box to be present (reduced timeout)
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            
            # Type search query
            search_box.send_keys("que dia es hoy")
            
            # Submit search
            search_box.submit()
            
            # Wait for results to load (reduced timeout)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            
            # Give a small delay for results to render
            time.sleep(1)
            
            # Extract results
            results = []
            
            # Try to get the featured snippet or answer box
            try:
                answer_box = driver.find_element(By.CSS_SELECTOR, "[data-attrid='wa:/description']")
                results.append(f"Respuesta destacada: {answer_box.text}")
            except:
                pass
            
            # Try to get date information from knowledge panel
            try:
                date_info = driver.find_element(By.CSS_SELECTOR, "[data-attrid='kc:/fun_fact:date']")
                results.append(f"Fecha: {date_info.text}")
            except:
                pass
            
            # Get search results (limit to 3 for speed)
            search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")[:3]
            
            for i, result in enumerate(search_results):
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3").text
                    results.append(f"\nResultado {i+1}: {title}")
                except:
                    continue
            
            if not results:
                return "No se encontraron resultados para 'que dia es hoy'"
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Error al buscar en Google: {str(e)}"
        finally:
            # Always close the browser
            if driver:
                driver.quit()