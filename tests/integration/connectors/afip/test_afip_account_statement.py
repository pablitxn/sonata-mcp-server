"""Integration test for AFIP Estado de Cuenta functionality.

This test validates the complete flow for obtaining account statements from AFIP,
including login, navigation, period selection, and debt extraction.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig, BrowserType
from src.captcha.chain import CaptchaChain
from src.captcha.circuit_breaker import CircuitBreakerConfig
from src.captcha.solvers import CapSolverAI
from src.connectors.afip.connector import AFIPConnector
from src.connectors.afip.interfaces import AFIPCredentials, LoginStatus
from src.connectors.afip.session import EncryptedSessionStorage

# Load environment variables
load_dotenv()


@pytest.mark.skipif(
    not os.getenv("AFIP_CUIT") or not os.getenv("AFIP_PASSWORD"),
    reason="AFIP credentials not configured"
)
@pytest.mark.integration
class TestAFIPEstadoCuenta:
    """Test class for AFIP Estado de Cuenta functionality."""

    @pytest.mark.asyncio
    async def test_get_account_statement_with_real_credentials(self):
        """Test the complete flow of getting account statement with real credentials."""
        # Setup browser factory
        browser_factory = BrowserEngineFactory()
        
        # Create browser config (non-headless for AFIP)
        browser_config = BrowserConfig(
            headless=True,
            viewport={"width": 1280, "height": 720}
        )
        
        # Setup session storage
        session_storage = EncryptedSessionStorage("/tmp/afip_test_sessions")
        
        # Setup captcha chain with available solvers
        captcha_chain = CaptchaChain()
        if os.getenv("CAPSOLVER_API_KEY"):
            captcha_chain.add_solver(
                CapSolverAI(os.getenv("CAPSOLVER_API_KEY")),
                CircuitBreakerConfig()
            )
        
        # Create connector
        connector = AFIPConnector(
            browser_factory=browser_factory,
            session_storage=session_storage,
            captcha_chain=captcha_chain,
            browser_config=browser_config
        )
        
        try:
            # Load real credentials from environment
            credentials = AFIPCredentials(
                cuit=os.getenv("AFIP_CUIT"),
                password=os.getenv("AFIP_PASSWORD")
            )
            
            print(f"\n1. Logging in with CUIT: {credentials.cuit}")
            
            # Step 1: Login
            login_status = await connector.login(credentials)
            assert login_status == LoginStatus.SUCCESS, f"Login failed with status: {login_status}"
            
            print("✓ Login successful")
            
            # Wait a bit for the dashboard to fully load
            await asyncio.sleep(3)
            
            # Step 2: Get account statement
            print("\n2. Getting account statement...")
            
            account_statement = await connector.get_account_statement(
                period_from="01/2025",
                period_to="06/2025",
                calculation_date="08/06/2025"
            )
            
            # Validate results
            assert account_statement is not None, "Failed to retrieve account statement"
            
            print(f"✓ Account statement retrieved successfully")
            print(f"  - Total debt: ${account_statement.total_debt:,.2f}")
            print(f"  - Screenshot saved at: {account_statement.screenshot_path}")
            print(f"  - Period: {account_statement.period_from} to {account_statement.period_to}")
            print(f"  - Calculation date: {account_statement.calculation_date}")
            
            # Verify screenshot file exists
            assert Path(account_statement.screenshot_path).exists(), "Screenshot file not found"
            
            # Verify the screenshot file has reasonable size (at least 10KB)
            file_size = Path(account_statement.screenshot_path).stat().st_size
            assert file_size > 10240, f"Screenshot file too small: {file_size} bytes"
            
            print(f"  - Screenshot file size: {file_size / 1024:.1f} KB")
            
            # Step 3: Logout
            print("\n3. Logging out...")
            logout_success = await connector.logout()
            assert logout_success, "Logout failed"
            
            print("✓ Logout successful")
            
            # Print summary
            print("\n" + "="*50)
            print("TEST COMPLETED SUCCESSFULLY")
            print("="*50)
            print(f"Total Debt: ${account_statement.total_debt:,.2f}")
            print(f"Screenshot: {account_statement.screenshot_path}")
            
        except Exception as e:
            print(f"\n✗ Test failed with error: {str(e)}")
            raise
        finally:
            # Ensure cleanup
            try:
                await connector.logout()
            except:
                pass


async def main():
    """Run the test manually for debugging."""
    test = TestAFIPEstadoCuenta()
    await test.test_get_account_statement_with_real_credentials()


if __name__ == "__main__":
    # This allows running the test directly with: python test_afip_account_statement.py
    asyncio.run(main())