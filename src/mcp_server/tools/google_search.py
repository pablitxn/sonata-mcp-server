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
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Create browser instance
            driver = webdriver.Chrome(options=chrome_options)
            
            # Navigate to Google
            driver.get("https://www.google.com")
            
            # Wait for search box to be present
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            
            # Type search query
            search_box.send_keys("que dia es hoy")
            
            # Submit search
            search_box.submit()
            
            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            
            # Give a bit more time for all results to render
            time.sleep(2)
            
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
            
            # Get search results
            search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for i, result in enumerate(search_results[:5]):  # Get first 5 results
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3").text
                    link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    snippet = result.find_element(By.CSS_SELECTOR, "span.aCOpRe, div.VwiC3b").text
                    
                    results.append(f"\nResultado {i+1}:")
                    results.append(f"Título: {title}")
                    results.append(f"URL: {link}")
                    results.append(f"Descripción: {snippet}")
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