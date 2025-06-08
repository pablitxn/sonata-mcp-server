"""AFIP connector implementation.

This module provides the main connector class for interacting with AFIP (Administración Federal 
de Ingresos Públicos - Argentina's Federal Tax Authority) web services. It handles authentication,
session management, captcha solving, and payment data retrieval.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from selenium.common.exceptions import TimeoutException

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig, IBrowserContext, IPage
from src.captcha.chain import CaptchaChain
from src.captcha.circuit_breaker import CircuitBreakerConfig
from src.captcha.solvers import AntiCaptchaSolver, CapSolverAI, TwoCaptchaSolver
from .interfaces import (
    AFIPCredentials,
    AFIPSession,
    IAFIPConnector,
    ISessionStorage,
    LoginStatus,
    Payment,
    PaymentStatus,
)
from .session import EncryptedSessionStorage

# Initialize structured logger for better debugging and monitoring
logger = structlog.get_logger()


class AFIPConnector(IAFIPConnector):
    """Main connector class for interacting with AFIP web services.
    
    This class implements the IAFIPConnector interface and provides functionality for:
    - User authentication with CUIT/password credentials
    - Automatic captcha solving using multiple solver services
    - Session persistence and restoration
    - Payment information retrieval
    - Secure session management with encryption
    
    The connector uses browser automation to interact with AFIP's web interface,
    handling common challenges like captchas and session timeouts.
    """

    # AFIP web application URLs
    LOGIN_URL = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"  # Main login page
    DASHBOARD_URL = "https://portalcf.cloud.afip.gob.ar/portal/app/"  # User dashboard after login
    PAYMENTS_URL = "https://portalcf.cloud.afip.gob.ar/portal/app/consultaDeuda"  # Payment query page

    def __init__(
            self,
            browser_factory: BrowserEngineFactory,
            session_storage: Optional[ISessionStorage] = None,
            captcha_chain: Optional[CaptchaChain] = None,
            browser_config: Optional[BrowserConfig] = None
    ):
        """Initialize the AFIP connector with required and optional components.
        
        Args:
            browser_factory: Factory for creating browser engine instances (Selenium/Playwright).
            session_storage: Storage backend for persisting user sessions. If not provided,
                           uses encrypted file storage in /tmp/afip_sessions.
            captcha_chain: Chain of captcha solvers to handle different captcha types.
                         If not provided, creates a default chain with available solvers.
            browser_config: Browser configuration options (viewport, headless mode, etc.).
                          If not provided, uses non-headless mode with 1280x720 viewport.
        """
        self.browser_factory = browser_factory
        self.session_storage = session_storage or EncryptedSessionStorage("/tmp/afip_sessions")
        self.captcha_chain = captcha_chain or self._create_default_captcha_chain()
        self.browser_config = browser_config or BrowserConfig(
            headless=False,  # AFIP detects and blocks headless browsers
            viewport={"width": 1280, "height": 720}
        )

        self._context: Optional[IBrowserContext] = None
        self._page: Optional[IPage] = None
        self._current_session: Optional[AFIPSession] = None

        self.logger = logger.bind(connector="afip")

    def _create_default_captcha_chain(self) -> CaptchaChain:
        """Create the default captcha solver chain with available services.
        
        This method creates a chain of captcha solvers with circuit breaker protection.
        The chain will try solvers in order of preference (CapSolver -> 2Captcha -> AntiCaptcha)
        until one successfully solves the captcha or all fail.
        
        The circuit breaker prevents repeated calls to failing services, improving
        reliability and reducing unnecessary API costs.
        
        Returns:
            CaptchaChain: Configured chain with available captcha solving services.
        """
        chain = CaptchaChain()

        # Circuit breaker configuration for handling solver failures
        # More aggressive settings to quickly detect and bypass failing services
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,      # Open circuit after 3 consecutive failures
            recovery_timeout=timedelta(minutes=5),  # Try again after 5 minutes
            success_threshold=2       # Require 2 successes to fully close circuit
        )

        # Add solvers in order of preference based on reliability and cost
        # Note: In production, these API keys should come from secure configuration
        if os.getenv("CAPSOLVER_API_KEY"):
            chain.add_solver(
                CapSolverAI(os.getenv("CAPSOLVER_API_KEY")),
                cb_config
            )

        if os.getenv("TWOCAPTCHA_API_KEY"):
            chain.add_solver(
                TwoCaptchaSolver(os.getenv("TWOCAPTCHA_API_KEY")),
                cb_config
            )

        if os.getenv("ANTICAPTCHA_API_KEY"):
            chain.add_solver(
                AntiCaptchaSolver(os.getenv("ANTICAPTCHA_API_KEY")),
                cb_config
            )

        return chain

    async def _initialize_browser(self) -> None:
        """Initialize the browser engine and create a new context.
        
        This method performs lazy initialization of the browser components:
        1. Creates a browser engine instance (Selenium by default)
        2. Creates a browser context with specific settings
        3. Opens a new page/tab for automation
        
        The browser is configured to bypass certain security restrictions
        that might interfere with automation while maintaining compatibility
        with AFIP's anti-bot measures.
        """
        if not self._context:
            # Use Selenium as the default engine (more stable for AFIP)
            from src.browser.interfaces import BrowserType
            engine = await self.browser_factory.create(
                BrowserType.SELENIUM,
                self.browser_config
            )

            # Create browser context with specific settings for AFIP compatibility
            self._context = await engine.create_context({
                "accept_downloads": False,      # Don't automatically download files
                "bypass_csp": True,            # Bypass Content Security Policy for injection
                "java_script_enabled": True     # JavaScript required for AFIP functionality
            })

            self._page = await self._context.new_page()
            self.logger.info("browser_initialized")

    async def _detect_captcha(self, page: IPage) -> Optional[Dict[str, Any]]:
        """Detect if there's a captcha on the current page.
        
        This method checks for different types of captchas that AFIP might use:
        1. Image-based captchas (traditional text in image)
        2. Google ReCaptcha v2
        
        The detection is done by examining the DOM for specific elements
        and JavaScript objects that indicate captcha presence.
        
        Args:
            page: The page instance to check for captchas.
            
        Returns:
            Optional[Dict[str, Any]]: Captcha information including type and selectors,
                                     or None if no captcha is detected.
        """
        try:
            # Check for different captcha types used by AFIP

            # 1. Image-based captcha detection
            # Look for image elements with 'captcha' in ID or src attributes
            has_image_captcha = await page.evaluate("""
                () => {
                    const captcha = document.querySelector('img[id*="captcha"], img[src*="captcha"]');
                    return captcha !== null;
                }
            """)

            if has_image_captcha:
                return {
                    "type": "image",
                    "image_selector": 'img[id*="captcha"], img[src*="captcha"]',  # Selector for captcha image
                    "input_selector": 'input[id*="captcha"], input[name*="captcha"]'  # Where to input solution
                }

            # 2. Google ReCaptcha v2 detection
            # Check for grecaptcha object or ReCaptcha container elements
            has_recaptcha = await page.evaluate("""
                () => {
                    return window.grecaptcha !== undefined || 
                           document.querySelector('.g-recaptcha') !== null;
                }
            """)

            if has_recaptcha:
                site_key = await page.evaluate("""
                    () => {
                        const elem = document.querySelector('.g-recaptcha');
                        return elem ? elem.getAttribute('data-sitekey') : null;
                    }
                """)

                return {
                    "type": "recaptcha_v2",
                    "site_key": site_key  # Required for API-based solving
                }

            return None

        except Exception as e:
            self.logger.error("captcha_detection_error", error=str(e))
            return None

    async def _solve_captcha(self, page: IPage, captcha_info: Dict[str, Any]) -> bool:
        """Attempt to solve a detected captcha using the configured solver chain.
        
        This method:
        1. Sends the captcha to the solver chain for resolution
        2. Applies the solution based on the captcha type
        3. Handles both image captchas and ReCaptcha v2
        
        For image captchas, the solution is typed into the input field.
        For ReCaptcha v2, the solution token is injected into the page.
        
        Args:
            page: The page containing the captcha.
            captcha_info: Information about the detected captcha (type, selectors, etc.).
            
        Returns:
            bool: True if the captcha was successfully solved and applied, False otherwise.
        """
        try:
            solution = await self.captcha_chain.solve(page, captcha_info)

            if not solution:
                self.logger.error("captcha_not_solved")
                return False

            # Apply the solution based on captcha type
            if captcha_info["type"] == "image":
                input_selector = captcha_info.get("input_selector")
                await page.fill(input_selector, solution)
                self.logger.info("captcha_solution_filled")

            elif captcha_info["type"] == "recaptcha_v2":
                # For ReCaptcha v2, inject the solution token into the page
                # This simulates a successful ReCaptcha verification
                await page.evaluate(f"""
                    (token) => {{
                        window.grecaptcha.getResponse = () => token;
                        document.getElementById('g-recaptcha-response').value = token;
                    }}
                """, solution)
                self.logger.info("recaptcha_token_injected")

            return True

        except Exception as e:
            self.logger.error("captcha_solve_error", error=str(e), exc_info=True)
            return False

    async def login(self, credentials: AFIPCredentials) -> LoginStatus:
        """Perform login to AFIP using provided credentials.
        
        This method handles the complete login flow:
        1. Attempts to restore a saved session (if available)
        2. If no valid session, performs fresh login
        3. Handles captcha challenges automatically
        4. Saves successful sessions for future use
        5. Detects various login failure scenarios
        
        Args:
            credentials: AFIP login credentials (CUIT and password).
            
        Returns:
            LoginStatus: The result of the login attempt (SUCCESS, FAILED, 
                        CAPTCHA_REQUIRED, CERTIFICATE_REQUIRED, etc.).
        """
        try:
            # Step 1: Try to restore a previously saved session
            # This avoids unnecessary logins and reduces captcha encounters
            if self.session_storage:
                saved_session = await self.session_storage.load(credentials.cuit)
                if saved_session and await self.session_storage.is_valid(saved_session):
                    if await self.restore_session(saved_session):
                        self.logger.info("session_restored", cuit=credentials.cuit)
                        return LoginStatus.SUCCESS

            # Step 2: Initialize browser if session restoration failed
            await self._initialize_browser()

            # Step 3: Navigate to the AFIP login page
            self.logger.info("navigating_to_login")
            await self._page.goto(self.LOGIN_URL, wait_until="networkidle")
            
            # Give the page time to fully load (AFIP can be slow)
            await asyncio.sleep(3)

            # Step 4: Wait for the login form to load
            # AFIP uses JSF (JavaServer Faces) which generates IDs like F1:username
            await self._page.wait_for_selector('input[name="F1:username"]', timeout=20000)

            # Step 5: Enter CUIT (numeric only - remove any hyphens if present)
            # AFIP's CUIT field only accepts numeric input
            cuit_numeric = credentials.cuit.replace("-", "")
            await self._page.fill('input[name="F1:username"]', cuit_numeric)
            
            # Click "Siguiente" (Next) to proceed
            await self._page.click('input[id="F1:btnSiguiente"]')
            
            # Wait for next page/field to load
            await asyncio.sleep(2)  # Small delay for page transition
            
            # Step 6: Enter password
            # Wait for password field to appear (AFIP uses F1:password)
            try:
                await self._page.wait_for_selector('input[name="F1:password"]', timeout=10000)
                await self._page.fill('input[name="F1:password"]', credentials.password)
            except TimeoutException:
                self.logger.error("password_field_not_found")
                return LoginStatus.FAILED

            # Step 7: Check for and handle captcha challenges
            captcha_info = await self._detect_captcha(self._page)
            if captcha_info:
                self.logger.info("captcha_detected", type=captcha_info["type"])

                # Attempt to solve the captcha automatically
                if not await self._solve_captcha(self._page, captcha_info):
                    # Return failure if captcha couldn't be solved
                    return LoginStatus.CAPTCHA_REQUIRED

            # Step 8: Submit the login form
            # AFIP uses "Ingresar" button with ID F1:btnIngresar
            await self._page.click('input[id="F1:btnIngresar"]')

            # Step 9: Wait for navigation and check login result
            await asyncio.sleep(3)  # Give time for navigation
            
            # Check if we've been redirected to the portal
            current_url = await self._page.evaluate("window.location.href")
            
            if "portalcf.cloud.afip.gob.ar/portal/app" in current_url:
                self.logger.info("login_successful", url=current_url)

                # Step 10: Login successful - save the session for future use
                # Extract all cookies from the browser context
                cookies = await self._context.get_cookies()

                # Create a new session object with the authentication data
                self._current_session = AFIPSession(
                    session_id=f"afip_{credentials.cuit}_{datetime.now().timestamp()}",
                    cuit=credentials.cuit,
                    cookies={c["name"]: c["value"] for c in cookies},  # Convert to dict format
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=2),  # AFIP sessions typically last 2 hours
                    is_valid=True
                )

                # Persist the session for future use
                if self.session_storage:
                    await self.session_storage.save(self._current_session)

                self.logger.info("login_successful", cuit=credentials.cuit)
                return LoginStatus.SUCCESS
            else:
                # Step 11: Login failed - determine the reason
                # Check if the failure is due to certificate requirement
                requires_cert = await self._page.evaluate("""
                    () => {
                        const text = document.body.innerText.toLowerCase();
                        return text.includes('certificado') || text.includes('certificate');
                    }
                """)

                if requires_cert:
                    # Some AFIP services require digital certificates
                    return LoginStatus.CERTIFICATE_REQUIRED

                # Generic login failure
                self.logger.error("login_failed", current_url=current_url)
                return LoginStatus.FAILED

        except Exception as e:
            # Log any unexpected errors during login
            self.logger.error("login_error", error=str(e), exc_info=True)
            return LoginStatus.FAILED

    async def logout(self) -> bool:
        """Logout from the current AFIP session.
        
        This method performs a complete logout:
        1. Clicks the logout button/link on AFIP website
        2. Invalidates the stored session
        3. Closes browser resources
        
        Returns:
            bool: True if logout was successful, False otherwise.
        """
        try:
            if not self._page:
                return True

            # Try different logout selectors (AFIP uses various logout buttons)
            logout_selectors = [
                'a[href*="logout"]',           # Logout links
                'button[id*="logout"]',        # Logout buttons with ID
                'a:has-text("Salir")',         # Spanish "Exit" links
                'button:has-text("Cerrar sesión")'  # Spanish "Close session" buttons
            ]

            # Attempt to click logout using various selectors
            for selector in logout_selectors:
                try:
                    await self._page.click(selector, timeout=5000)
                    break
                except:
                    # Try next selector if current one fails
                    continue

            # Invalidate the stored session to prevent reuse
            if self._current_session and self.session_storage:
                await self.session_storage.delete(self._current_session.cuit)

            # Clear current session reference
            self._current_session = None

            # Clean up browser resources
            if self._page:
                await self._page.close()
                self._page = None

            if self._context:
                await self._context.close()
                self._context = None

            self.logger.info("logout_successful")
            return True

        except Exception as e:
            self.logger.error("logout_error", error=str(e))
            return False

    async def get_pending_payments(self) -> List[Payment]:
        """Retrieve the list of pending payments from AFIP.
        
        This method:
        1. Navigates to the payments consultation page
        2. Extracts payment information from the HTML table
        3. Parses and converts the data to Payment objects
        4. Handles different date and currency formats used by AFIP
        
        Returns:
            List[Payment]: List of pending payment objects with amount, due date,
                          status, and other relevant information.
        """
        try:
            # Ensure we have an active session
            if not self._current_session:
                self.logger.error("no_active_session")
                return []

            # Navigate to the payments page
            self.logger.info("navigating_to_payments")
            await self._page.goto(self.PAYMENTS_URL, wait_until="networkidle")

            # Wait for the payments table to load
            await self._page.wait_for_selector('table[id*="deuda"], .tabla-deudas', timeout=15000)

            # Extract payment information from the HTML table
            payments_data = await self._page.evaluate("""
                () => {
                    const payments = [];
                    // Find all table rows in payment tables
                    const rows = document.querySelectorAll('table[id*="deuda"] tr, .tabla-deudas tr');
                    
                    // Process each row (skip header row)
                    for (let i = 1; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll('td');
                        // Ensure row has minimum required cells
                        if (cells.length >= 5) {
                            payments.push({
                                id: cells[0].innerText.trim(),          // Payment ID
                                description: cells[1].innerText.trim(),  // Payment description
                                amount: cells[2].innerText.trim(),       // Amount in currency format
                                due_date: cells[3].innerText.trim(),     // Due date
                                status: cells[4].innerText.trim(),       // Payment status
                                tax_type: cells[5] ? cells[5].innerText.trim() : '',  // Type of tax
                                period: cells[6] ? cells[6].innerText.trim() : ''     // Tax period
                            });
                        }
                    }
                    
                    return payments;
                }
            """)

            # Convert raw data to Payment objects
            payments = []
            for data in payments_data:
                try:
                    # Parse amount from Argentine currency format
                    # Format: $10.500,50 -> 10500.50 (thousands separator is dot, decimal is comma)
                    amount_str = data["amount"].replace("$", "").replace(".", "")  # Remove currency symbol and thousands separator
                    amount_str = amount_str.replace(",", ".")  # Replace decimal comma with dot
                    amount = float(amount_str)

                    # Parse date from DD/MM/YYYY format
                    due_date = datetime.strptime(data["due_date"], "%d/%m/%Y")

                    # Map Spanish status text to enum values
                    status_map = {
                        "pendiente": PaymentStatus.PENDING,   # Pending
                        "vencido": PaymentStatus.OVERDUE,     # Overdue
                        "pagado": PaymentStatus.PAID,         # Paid
                        "parcial": PaymentStatus.PARTIAL      # Partially paid
                    }
                    status = status_map.get(
                        data["status"].lower(),
                        PaymentStatus.PENDING  # Default to pending if status unknown
                    )

                    # Create Payment object
                    payment = Payment(
                        id=data["id"],
                        description=data["description"],
                        amount=amount,
                        due_date=due_date,
                        status=status,
                        tax_type=data["tax_type"],
                        period=data["period"]
                    )

                    payments.append(payment)

                except Exception as e:
                    # Log parsing errors but continue processing other payments
                    self.logger.warning(
                        "payment_parse_error",
                        data=data,
                        error=str(e)
                    )

            self.logger.info("payments_retrieved", count=len(payments))
            return payments

        except Exception as e:
            self.logger.error("get_payments_error", error=str(e), exc_info=True)
            return []

    async def get_session(self) -> Optional[AFIPSession]:
        """Get the current active session information.
        
        This method provides access to the current session data,
        which includes session ID, CUIT, cookies, and expiration time.
        
        Returns:
            Optional[AFIPSession]: The current session object if logged in, None otherwise.
        """
        return self._current_session

    async def restore_session(self, session: AFIPSession) -> bool:
        """Restore a previously saved session to avoid re-authentication.
        
        This method attempts to restore a session by:
        1. Validating the session hasn't expired
        2. Setting the stored cookies in the browser
        3. Navigating to AFIP and verifying the session is still valid
        
        This helps reduce captcha encounters and improves user experience
        by maintaining sessions across connector instances.
        
        Args:
            session: The session object to restore containing cookies and metadata.
            
        Returns:
            bool: True if the session was successfully restored and is valid,
                 False if the session is invalid or restoration failed.
        """
        try:
            # Step 1: Verify session validity before attempting restoration
            if not await self.session_storage.is_valid(session):
                self.logger.warning("session_invalid_for_restore", cuit=session.cuit)
                return False

            # Step 2: Initialize browser if not already done
            await self._initialize_browser()

            # Step 3: Navigate to AFIP login page first
            await self._page.goto(self.LOGIN_URL)

            # Step 4: Set all stored cookies in the browser context
            cookies_list = [
                {
                    "name": name,
                    "value": value,
                    "domain": ".afip.gob.ar",  # AFIP domain
                    "path": "/"                  # Root path
                }
                for name, value in session.cookies.items()
            ]
            await self._context.set_cookies(cookies_list)

            # Step 5: Navigate to dashboard to test if session is valid
            await self._page.goto(self.DASHBOARD_URL)

            # Step 6: Check if we're actually logged in by looking for logout button
            is_logged_in = await self._page.evaluate("""
                () => {
                    // Look for logout button/link as indicator of active session
                    return document.querySelector('a[href*="logout"], button[id*="logout"]') !== null;
                }
            """)

            if is_logged_in:
                # Session is valid - save it as current
                self._current_session = session
                self.logger.info("session_restored_successfully", cuit=session.cuit)
                return True
            else:
                # Session is no longer valid on AFIP side
                self.logger.warning("session_restore_failed", cuit=session.cuit)
                return False

        except Exception as e:
            self.logger.error(
                "session_restore_error",
                error=str(e),
                exc_info=True
            )
            return False
