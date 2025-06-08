from mcp.server.fastmcp import FastMCP, Context
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import asyncio


async def search_google_today(ctx: Context = None) -> str:
    """Navigate to Google, search for 'que dia es hoy' and return the results.
    
    This tool uses Selenium to perform a Google search for 'what day is today' in Spanish
    and returns the search results.
    
    Args:
        ctx: The MCP server provided context (optional for testing)
        
    Returns:
        str: The search results or error message
    """
    driver = None
    try:
        print("🚀 Iniciando búsqueda en Google...")
        
        # Configure Chrome options for faster execution
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Create browser instance
        print("🌐 Creando instancia del navegador...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # Navigate to Google
        print("📍 Navegando a Google.com...")
        driver.get("https://www.google.com")
        
        # Handle cookies if present
        time.sleep(2)
        try:
            accept_button = driver.find_element(By.XPATH, "//button[contains(., 'Aceptar') or contains(., 'Accept') or contains(., 'Acepto')]")
            accept_button.click()
            print("🍪 Cookies aceptadas")
            time.sleep(1)
        except:
            print("ℹ️  No se encontró botón de cookies")
        
        # Wait for search box to be present
        print("🔍 Buscando caja de búsqueda...")
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        
        # Type search query
        print("⌨️  Escribiendo consulta: 'que dia es hoy'")
        search_box.send_keys("que dia es hoy")
        
        # Submit search
        search_box.submit()
        
        # Wait for results to load (reduced timeout)
        print("⏳ Esperando resultados...")
        try:
            # Try different selectors for results
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "search")),
                    EC.presence_of_element_located((By.ID, "rcnt")),
                    EC.presence_of_element_located((By.CLASS_NAME, "g"))
                )
            )
        except TimeoutException:
            print("⚠️  No se encontró el contenedor de resultados, continuando...")
        
        # Give a small delay for results to render
        time.sleep(1)
        
        # Extract results
        results = []
        
        print("📊 Buscando información de fecha...")
        
        # Method 1: Look for date cards
        try:
            date_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'card-section') or contains(@class, 'kno-rdesc') or contains(@class, 'hgKElc')]")
            for card in date_cards[:2]:
                text = card.text.strip()
                if text and len(text) > 10:
                    results.append(f"📅 {text}")
                    print(f"   → Encontrado: {text[:100]}...")
        except:
            print("   ℹ️  No se encontraron cards de fecha")
        
        # Method 2: Search for date information in the page text
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')
            
            for line in lines:
                if any(month in line.lower() for month in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']):
                    if len(line) > 15 and line not in str(results):
                        results.append(f"📅 {line}")
                        print(f"   → Fecha: {line}")
                        if len(results) >= 3:
                            break
        except:
            print("   ℹ️  Error al buscar en el texto de la página")
        
        # Get search result titles if no date info found
        if len(results) < 2:
            print("📄 Extrayendo títulos de resultados...")
            try:
                titles = driver.find_elements(By.CSS_SELECTOR, "h3")[:3]
                for i, title_elem in enumerate(titles):
                    title = title_elem.text.strip()
                    if title:
                        results.append(f"🔗 {title}")
                        print(f"   → Título {i+1}: {title}")
            except:
                print("   ℹ️  No se encontraron títulos")
        
        if not results:
            return "❌ No se encontraron resultados para 'que dia es hoy'"
        
        print("\n✅ Búsqueda completada exitosamente!")
        return "\n".join(results)
        
    except TimeoutException as e:
        error_msg = f"⏱️ Error de timeout: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ Error al buscar en Google: {str(e)}"
        print(error_msg)
        return error_msg
    finally:
        # Always close the browser
        if driver:
            print("🧹 Cerrando navegador...")
            driver.quit()


def register_google_search_tool(mcp: FastMCP):
    """Register Google search tool with the MCP server."""
    
    @mcp.tool()
    async def search_google_today_wrapper(ctx: Context) -> str:
        """Navigate to Google, search for 'que dia es hoy' and return the results."""
        return await search_google_today(ctx)


async def test_google_search():
    """Test function to run the Google search independently."""
    print("=== 🧪 Test de búsqueda en Google ===\n")
    result = await search_google_today()
    print("\n=== 📋 Resultado final ===")
    print(result)
    print("\n=== ✅ Test completado ===")


if __name__ == "__main__":
    # Run the test when the file is executed directly
    asyncio.run(test_google_search())