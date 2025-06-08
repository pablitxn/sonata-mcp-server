"""Example usage of the AFIP connector."""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig
from src.captcha.chain import CaptchaChain
from src.captcha.circuit_breaker import CircuitBreakerConfig
from src.captcha.solvers import CapSolverAI, TwoCaptchaSolver
from src.connectors.afip.connector import AFIPConnector
from src.connectors.afip.interfaces import AFIPCredentials, LoginStatus
from src.connectors.afip.session import EncryptedSessionStorage


async def main():
    """Example usage of the AFIP connector."""

    # Configure the browser (using Selenium)
    browser_config = BrowserConfig(
        headless=False,  # AFIP detects headless, better to use with window
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    # Create browser factory
    browser_factory = BrowserEngineFactory()

    # Configure secure session storage
    # If no encryption key is provided, it will generate one automatically
    session_storage = EncryptedSessionStorage(
        storage_path="/tmp/afip_sessions",
        encryption_key=None  # Will auto-generate a key
    )

    # Configure captcha solvers chain
    captcha_chain = CaptchaChain()

    # Circuit breaker configuration
    cb_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=timedelta(minutes=5),
        success_threshold=2
    )

    # Add solvers in order of preference
    if os.getenv("CAPSOLVER_API_KEY"):
        captcha_chain.add_solver(
            CapSolverAI(os.getenv("CAPSOLVER_API_KEY")),
            cb_config
        )

    if os.getenv("TWOCAPTCHA_API_KEY"):
        captcha_chain.add_solver(
            TwoCaptchaSolver(os.getenv("TWOCAPTCHA_API_KEY")),
            cb_config
        )

    # Create the connector
    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage,
        captcha_chain=captcha_chain,
        browser_config=browser_config
    )

    try:
        # Credentials from environment variables
        credentials = AFIPCredentials(
            cuit=os.getenv("AFIP_CUIT", "20123456789"),  # Default without hyphens
            password=os.getenv("AFIP_PASSWORD", "password")
        )

        print(f"Starting login to AFIP for CUIT: {credentials.cuit}")

        # Attempt login
        login_status = await connector.login(credentials)

        if login_status == LoginStatus.SUCCESS:
            print("✅ Login successful!")

            # Get session info
            session = await connector.get_session()
            if session:
                print(f"Session valid until: {session.expires_at}")

            # Check pending payments
            print("\nChecking pending payments...")
            payments = await connector.get_pending_payments()

            if payments:
                print(f"\n📋 Found {len(payments)} pending payments:")

                total = 0
                for payment in payments:
                    print(f"\n- ID: {payment.id}")
                    print(f"  Description: {payment.description}")
                    print(f"  Amount: ${payment.amount:,.2f}")
                    print(f"  Due date: {payment.due_date.strftime('%d/%m/%Y')}")
                    print(f"  Status: {payment.status.value}")
                    print(f"  Type: {payment.tax_type}")
                    print(f"  Period: {payment.period}")

                    total += payment.amount

                print(f"\n💰 Total pending: ${total:,.2f}")
            else:
                print("✨ No pending payments!")

        elif login_status == LoginStatus.CAPTCHA_REQUIRED:
            print("❌ Could not automatically solve the captcha")

        elif login_status == LoginStatus.CERTIFICATE_REQUIRED:
            print("🔐 Digital certificate required for login")

        else:
            print("❌ Login error")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Logout and clean resources
        print("\nLogging out...")
        await connector.logout()
        print("✅ Session closed")


# Example usage with restoring existing session
async def example_with_session_restore():
    """Example restoring a saved session."""

    browser_factory = BrowserEngineFactory()
    session_storage = EncryptedSessionStorage("/tmp/afip_sessions")

    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage
    )

    cuit = "20-12345678-9"

    # Attempt to load saved session
    saved_session = await session_storage.load(cuit)

    if saved_session and await session_storage.is_valid(saved_session):
        print("📂 Saved session found, attempting to restore...")

        if await connector.restore_session(saved_session):
            print("✅ Session restored successfully!")

            # Use restored session
            payments = await connector.get_pending_payments()
            print(f"Pending payments: {len(payments)}")
        else:
            print("❌ Could not restore the session")
    else:
        print("No valid saved session found")


if __name__ == "__main__":
    # To run:
    # python -m src.connectors.afip.example

    asyncio.run(main())

    # Example restoring session
    # asyncio.run(example_with_session_restore())
