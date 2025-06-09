"""AFIP connector implementation.

This module provides the main connector class for interacting with AFIP (Administración Federal 
de Ingresos Públicos - Argentina's Federal Tax Authority) web services. It handles authentication,
session management, captcha solving, and payment data retrieval.
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium.common.exceptions import TimeoutException

from browser.factory import BrowserEngineFactory
from browser.interfaces import BrowserConfig, IBrowserContext, IPage
from captcha.chain import CaptchaChain
from captcha.circuit_breaker import CircuitBreakerConfig
from captcha.solvers import AntiCaptchaSolver, CapSolverAI, TwoCaptchaSolver
from config.mcp_logger import logger
from ...telemetry.factory import get_telemetry_provider
from ...telemetry.interfaces import ITelemetryProvider
from .interfaces import (
    AFIPCredentials,
    AFIPSession,
    IAFIPConnector,
    ISessionStorage,
    LoginStatus,
    Payment,
    PaymentStatus,
    AccountStatement,
)
from .session import EncryptedSessionStorage


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
    
    _telemetry: ITelemetryProvider = get_telemetry_provider()

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
            headless=True,  # Use headless mode for better performance
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
            failure_threshold=3,  # Open circuit after 3 consecutive failures
            recovery_timeout=timedelta(minutes=5),  # Try again after 5 minutes
            success_threshold=2  # Require 2 successes to fully close circuit
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
            from browser.interfaces import BrowserType
            
            self.logger.info("connector._initialize_browser: starting browser initialization",
                           browser_type="SELENIUM",
                           headless=self.browser_config.headless,
                           viewport=self.browser_config.viewport)
            
            engine = await self.browser_factory.create(
                BrowserType.SELENIUM,
                self.browser_config
            )
            
            self.logger.info("connector._initialize_browser: engine created successfully")

            # Create browser context with specific settings for AFIP compatibility
            context_options = {
                "accept_downloads": False,  # Don't automatically download files
                "bypass_csp": True,  # Bypass Content Security Policy for injection
                "java_script_enabled": True  # JavaScript required for AFIP functionality
            }
            
            self.logger.info("connector._initialize_browser: creating context", options=context_options)
            
            self._context = await engine.create_context(context_options)

            self._page = await self._context.new_page()
            self.logger.info("connector._initialize_browser: browser initialized successfully")

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
                self.logger.info("connector._detect_captcha: image captcha detected")
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
                
                self.logger.info("connector._detect_captcha: recaptcha v2 detected", site_key=site_key)

                return {
                    "type": "recaptcha_v2",
                    "site_key": site_key  # Required for API-based solving
                }

            return None

        except Exception as e:
            self.logger.error("connector._detect_captcha: error detecting captcha", 
                            error=str(e), 
                            page_url=await page.evaluate("window.location.href") if page else None)
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
            self.logger.info("connector._solve_captcha: attempting to solve captcha",
                           captcha_type=captcha_info.get("type"))
            
            solution = await self.captcha_chain.solve(page, captcha_info)

            if not solution:
                self.logger.error("connector._solve_captcha: captcha not solved",
                                captcha_type=captcha_info.get("type"))
                return False

            # Apply the solution based on captcha type
            if captcha_info["type"] == "image":
                input_selector = captcha_info.get("input_selector")
                self.logger.info("connector._solve_captcha: filling image captcha solution",
                               selector=input_selector,
                               solution_length=len(solution))
                await page.fill(input_selector, solution)
                self.logger.info("connector._solve_captcha: image captcha solution filled successfully")

            elif captcha_info["type"] == "recaptcha_v2":
                # For ReCaptcha v2, inject the solution token into the page
                # This simulates a successful ReCaptcha verification
                self.logger.info("connector._solve_captcha: injecting recaptcha token",
                               token_length=len(solution))
                await page.evaluate(f"""
                    (token) => {{
                        window.grecaptcha.getResponse = () => token;
                        document.getElementById('g-recaptcha-response').value = token;
                    }}
                """, solution)
                self.logger.info("connector._solve_captcha: recaptcha token injected successfully")

            return True

        except Exception as e:
            self.logger.error("connector._solve_captcha: error solving captcha", 
                            error=str(e), 
                            captcha_type=captcha_info.get("type"),
                            exc_info=True)
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
        # Start telemetry trace for login operation
        with self._telemetry.trace("afip_login") as trace:
            trace.add_metadata({
                "cuit": credentials.cuit[:2] + "***" + credentials.cuit[-2:],  # Masked CUIT
                "attempt_session_restore": bool(self.session_storage)
            })
            
            try:
                # Step 1: Try to restore a previously saved session
                # This avoids unnecessary logins and reduces captcha encounters
                self.logger.info("connector.login: starting login process", cuit=credentials.cuit)
                
                if self.session_storage:
                    with trace.span("session_restore") as span:
                        self.logger.info("connector.login: checking for saved session")
                        saved_session = await self.session_storage.load(credentials.cuit)
                        if saved_session and await self.session_storage.is_valid(saved_session):
                            self.logger.info("connector.login: found valid saved session, attempting restore")
                            if await self.restore_session(saved_session):
                                self.logger.info("connector.login: session restored successfully", cuit=credentials.cuit)
                                span.add_metadata({"restored": True})
                                trace.add_metadata({"login_method": "session_restore"})
                                return LoginStatus.SUCCESS
                            else:
                                self.logger.warning("connector.login: session restore failed, proceeding with fresh login")
                                span.add_metadata({"restored": False})

                # Step 2: Initialize browser if session restoration failed
                await self._initialize_browser()

                # Step 3: Navigate to the AFIP login page
                self.logger.info("connector.login: navigating to login page", url=self.LOGIN_URL)
                await self._page.goto(self.LOGIN_URL, wait_until="networkidle")
                self.logger.info("connector.login: login page loaded")

                # Give the page time to fully load (AFIP can be slow)
                await asyncio.sleep(3)

                # Step 4: Wait for the login form to load
                # AFIP uses JSF (JavaServer Faces) which generates IDs like F1:username
                self.logger.info("connector.login: waiting for username field")
                await self._page.wait_for_selector('input[name="F1:username"]', timeout=20000)
                self.logger.info("connector.login: username field found")

                # Step 5: Enter CUIT (numeric only - remove any hyphens if present)
                # AFIP's CUIT field only accepts numeric input
                cuit_numeric = credentials.cuit.replace("-", "")
                self.logger.info("connector.login: filling username field", 
                               cuit_length=len(cuit_numeric),
                               cuit_masked=f"{cuit_numeric[:2]}...{cuit_numeric[-2:]}")
                await self._page.fill('input[name="F1:username"]', cuit_numeric)

                # Click "Siguiente" (Next) to proceed
                self.logger.info("connector.login: clicking next button")
                await self._page.click('input[id="F1:btnSiguiente"]')

                # Wait for next page/field to load
                await asyncio.sleep(2)  # Small delay for page transition

                # Step 6: Enter password
                # Wait for password field to appear (AFIP uses F1:password)
                try:
                    self.logger.info("connector.login: waiting for password field")
                    await self._page.wait_for_selector('input[name="F1:password"]', timeout=10000)
                    self.logger.info("connector.login: password field found, filling credentials")
                    await self._page.fill('input[name="F1:password"]', credentials.password)
                    self.logger.info("connector.login: password filled")
                except TimeoutException:
                    self.logger.error("connector.login: password field not found - timeout",
                                    current_url=await self._page.evaluate("window.location.href"))
                    return LoginStatus.FAILED

                # Step 7: Check for and handle captcha challenges
                with trace.span("captcha_handling") as captcha_span:
                    self.logger.info("connector.login: checking for captcha")
                    captcha_info = await self._detect_captcha(self._page)
                    if captcha_info:
                        self.logger.info("connector.login: captcha detected", type=captcha_info["type"])
                        captcha_span.add_metadata({"captcha_type": captcha_info["type"]})

                        # Attempt to solve the captcha automatically
                        if not await self._solve_captcha(self._page, captcha_info):
                            # Return failure if captcha couldn't be solved
                            self.logger.error("connector.login: captcha could not be solved")
                            captcha_span.add_metadata({"solved": False})
                            trace.add_metadata({"failure_reason": "captcha_not_solved"})
                            return LoginStatus.CAPTCHA_REQUIRED
                        captcha_span.add_metadata({"solved": True})
                    else:
                        self.logger.info("connector.login: no captcha detected")
                        captcha_span.add_metadata({"captcha_present": False})

                # Step 8: Submit the login form
                # AFIP uses "Ingresar" button with ID F1:btnIngresar
                self.logger.info("connector.login: clicking login button")
                await self._page.click('input[id="F1:btnIngresar"]')
                self.logger.info("connector.login: login form submitted")

                # Step 9: Wait for navigation and check login result
                self.logger.info("connector.login: waiting for navigation after login")
                await asyncio.sleep(3)  # Give time for navigation

                # Check if we've been redirected to the portal
                current_url = await self._page.evaluate("window.location.href")
                self.logger.info("connector.login: checking login result", current_url=current_url)

                if "portalcf.cloud.afip.gob.ar/portal/app" in current_url:
                    self.logger.info("connector.login: login successful, redirected to portal", url=current_url)

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
                        self.logger.info("connector.login: saving session for future use")
                        await self.session_storage.save(self._current_session)

                    self.logger.info("connector.login: login completed successfully", 
                                   cuit=credentials.cuit,
                                   session_id=self._current_session.session_id)
                    trace.add_metadata({
                        "login_method": "fresh_login",
                        "success": True,
                        "session_saved": bool(self.session_storage)
                    })
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
                        self.logger.warning("connector.login: certificate required for this service")
                        return LoginStatus.CERTIFICATE_REQUIRED

                    # Generic login failure
                    self.logger.error("connector.login: login failed - not redirected to portal", 
                                    current_url=current_url,
                                    page_title=await self._page.title())
                    return LoginStatus.FAILED

            except Exception as e:
                # Log any unexpected errors during login
                self.logger.error("connector.login: unexpected error during login", 
                                error=str(e), 
                                error_type=type(e).__name__,
                                exc_info=True)
                trace.add_metadata({
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
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
                'a[href*="logout"]',  # Logout links
                'button[id*="logout"]',  # Logout buttons with ID
                'a:has-text("Salir")',  # Spanish "Exit" links
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
                self.logger.error("connector.get_pending_payments: no active session")
                return []

            # Navigate to the payments page
            self.logger.info("connector.get_pending_payments: navigating to payments page", 
                           url=self.PAYMENTS_URL)
            await self._page.goto(self.PAYMENTS_URL, wait_until="networkidle")
            self.logger.info("connector.get_pending_payments: payments page loaded")

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
                    amount_str = data["amount"].replace("$", "").replace(".",
                                                                         "")  # Remove currency symbol and thousands separator
                    amount_str = amount_str.replace(",", ".")  # Replace decimal comma with dot
                    amount = float(amount_str)

                    # Parse date from DD/MM/YYYY format
                    due_date = datetime.strptime(data["due_date"], "%d/%m/%Y")

                    # Map Spanish status text to enum values
                    status_map = {
                        "pendiente": PaymentStatus.PENDING,  # Pending
                        "vencido": PaymentStatus.OVERDUE,  # Overdue
                        "pagado": PaymentStatus.PAID,  # Paid
                        "parcial": PaymentStatus.PARTIAL  # Partially paid
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
                        "connector.get_pending_payments: error parsing payment data",
                        data=data,
                        error=str(e),
                        error_type=type(e).__name__
                    )

            self.logger.info("connector.get_pending_payments: payments retrieved successfully", 
                           count=len(payments),
                           total_amount=sum(p.amount for p in payments))
            return payments

        except Exception as e:
            self.logger.error("connector.get_pending_payments: error retrieving payments", 
                            error=str(e),
                            error_type=type(e).__name__,
                            exc_info=True)
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
            self.logger.info("connector.restore_session: attempting to restore session", 
                           cuit=session.cuit,
                           session_id=session.session_id)
            
            if not await self.session_storage.is_valid(session):
                self.logger.warning("connector.restore_session: session is invalid", 
                                  cuit=session.cuit,
                                  expires_at=session.expires_at)
                return False

            # Step 2: Initialize browser if not already done
            await self._initialize_browser()

            # Step 3: Navigate to AFIP login page first
            self.logger.info("connector.restore_session: navigating to login page")
            await self._page.goto(self.LOGIN_URL)

            # Step 4: Set all stored cookies in the browser context
            cookies_list = [
                {
                    "name": name,
                    "value": value,
                    "domain": ".afip.gob.ar",  # AFIP domain
                    "path": "/"  # Root path
                }
                for name, value in session.cookies.items()
            ]
            self.logger.info("connector.restore_session: setting cookies", 
                           cookie_count=len(cookies_list))
            await self._context.set_cookies(cookies_list)

            # Step 5: Navigate to dashboard to test if session is valid
            self.logger.info("connector.restore_session: navigating to dashboard to verify session")
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
                self.logger.info("connector.restore_session: session restored successfully", 
                               cuit=session.cuit,
                               session_id=session.session_id)
                return True
            else:
                # Session is no longer valid on AFIP side
                self.logger.warning("connector.restore_session: session no longer valid on AFIP", 
                                  cuit=session.cuit,
                                  current_url=await self._page.evaluate("window.location.href"))
                return False

        except Exception as e:
            self.logger.error(
                "connector.restore_session: error during session restoration",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return False

    async def get_account_statement(
            self,
            period_from: Optional[str] = None,
            period_to: Optional[str] = None,
            calculation_date: Optional[str] = None,
    ) -> Optional[AccountStatement]:
        """
        Fetch the “Estado de cuenta” (account statement) and return debt data
        plus a full-page screenshot.

        Flow
        ----
        1.  Click the *Estado de cuenta* shortcut on the AFIP dashboard
        2.  Detect / open the tab `P02_ctacte.asp`
        3.  Fill period & calculation-date fields
        4.  Press **Cálculo de deuda**
        5.  Screenshot the results
        6.  Parse “Total Saldo Deudor”

        Parameters
        ----------
        period_from : str  – `MM/YYYY` (default **01/2025**)
        period_to   : str  – `MM/YYYY` (default **06/2025**)
        calculation_date : str – `DD/MM/YYYY` (default **08/06/2025**)

        Returns
        -------
        AccountStatement | None
        """
        try:
            # Log method entry with parameters
            self.logger.info(
                "connector.get_account_statement: method entry",
                period_from=period_from,
                period_to=period_to,
                calculation_date=calculation_date
            )
            
            # ------------------------------------------------------------------
            # Guards & defaults
            # ------------------------------------------------------------------
            if not self._current_session:
                self.logger.error("connector.get_account_statement: no active session available")
                return None

            period_from = period_from or "01/2025"
            period_to = period_to or "06/2025"
            calculation_date = calculation_date or "08/06/2025"
            
            self.logger.info(
                "connector.get_account_statement: using parameters",
                period_from=period_from,
                period_to=period_to,
                calculation_date=calculation_date,
                cuit=self._current_session.cuit
            )

            # Navigate to dashboard
            self.logger.info(
                "connector.get_account_statement: navigating to dashboard",
                url=self.DASHBOARD_URL
            )
            await self._page.goto(self.DASHBOARD_URL, wait_until="networkidle")
            await asyncio.sleep(2)  # dashboard JS widgets finish mounting
            
            self.logger.info(
                "connector.get_account_statement: dashboard loaded",
                current_url=await self._page.evaluate("window.location.href")
            )

            # ------------------------------------------------------------------
            # Step 1 – click the “Estado de cuenta” tile  (CSS-only strategy)
            # ------------------------------------------------------------------
            self.logger.info("connector.get_account_statement: starting to click Estado de cuenta button")

            container_sel = "#contenidoAccesosPrincipales"
            try:
                self.logger.info(
                    "connector.get_account_statement: waiting for container",
                    selector=container_sel
                )
                container = await self._page.wait_for_selector(container_sel, timeout=5_000)
                self.logger.info("connector.get_account_statement: container found")
            except Exception as e:
                self.logger.error(
                    "connector.get_account_statement: shortcut container not found",
                    selector=container_sel,
                    error=str(e)
                )
                return None

            links = await container.query_selector_all("a.accesoPrincipal")
            self.logger.info(
                "connector.get_account_statement: found links",
                count=len(links)
            )

            clicked = False
            for i, link in enumerate(links):
                # inner_text collapses whitespace & gets *visible* label
                text = (await link.inner_text()).casefold()
                self.logger.debug(
                    "connector.get_account_statement: checking link",
                    index=i,
                    text=text
                )
                if "estado de cuenta" in text:
                    self.logger.info(
                        "connector.get_account_statement: found Estado de cuenta link",
                        text=text
                    )
                    await self._page.evaluate(
                        "(el) => el.scrollIntoView({block:'center'})", link
                    )
                    await link.click()
                    clicked = True
                    self.logger.info("connector.get_account_statement: Estado de cuenta link clicked")
                    break

            # fallback – unique dollar-icon in case label changes
            if not clicked:
                try:
                    fallback_selector = f"{container_sel} i.fa-dollar"
                    self.logger.info(
                        "connector.get_account_statement: trying fallback selector",
                        selector=fallback_selector
                    )
                    await self._page.click(fallback_selector, timeout=2_000)
                    clicked = True
                    self.logger.info("connector.get_account_statement: Estado de cuenta icon clicked (fallback)")
                except Exception as e:
                    self.logger.warning(
                        "connector.get_account_statement: fallback selector failed",
                        selector=fallback_selector,
                        error=str(e)
                    )

            if not clicked:
                self.logger.error("connector.get_account_statement: Estado de cuenta button not found")
                return None

            # ------------------------------------------------------------------
            # Step 2 – switch to / open the P02_ctacte.asp tab
            # ------------------------------------------------------------------
            self.logger.info("connector.get_account_statement: waiting for new tab to open")
            await asyncio.sleep(3)

            pages = await self._context.get_pages()
            self.logger.info(
                "connector.get_account_statement: checking pages for account statement tab",
                count=len(pages)
            )
            
            account_page = None
            for i, p in enumerate(pages):
                url = await p.evaluate("location.href")
                self.logger.info(
                    "connector.get_account_statement: checking page",
                    index=i,
                    url=url
                )
                if "P02_ctacte.asp" in url:
                    account_page = p
                    self.logger.info(
                        "connector.get_account_statement: found account statement page",
                        index=i,
                        url=url
                    )
                    break

            if account_page is None:
                direct_url = "https://servicios2.afip.gob.ar/tramites_con_clave_fiscal/ccam/P02_ctacte.asp"
                self.logger.warning(
                    "connector.get_account_statement: new tab not detected, navigating directly",
                    url=direct_url
                )
                account_page = await self._context.new_page()
                await account_page.goto(direct_url)
                self.logger.info(
                    "connector.get_account_statement: direct navigation complete",
                    current_url=await account_page.evaluate("window.location.href")
                )

            await asyncio.sleep(3)

            # Debug: Save account page HTML
            if os.getenv("AFIP_DEBUG", "false").lower() == "true":
                debug_path = "/tmp/afip_account_page.html"
                self.logger.info(
                    "connector.get_account_statement: saving debug HTML",
                    path=debug_path
                )
                html = await account_page.content()
                with open(debug_path, "w") as f:
                    f.write(html)
                self.logger.info(
                    "connector.get_account_statement: debug HTML saved",
                    path=debug_path,
                    size=len(html)
                )

            # ------------------------------------------------------------------
            # Step 3 – fill period & calculation date
            # ------------------------------------------------------------------
            self.logger.info(
                "connector.get_account_statement: filling form fields",
                period_from=period_from,
                period_to=period_to,
                calculation_date=calculation_date,
            )

            try:
                selector = 'input[name="perdesde2"]'
                self.logger.info(
                    "connector.get_account_statement: filling period_from field",
                    selector=selector,
                    value=period_from
                )
                await account_page.fill(selector, period_from)
                self.logger.info("connector.get_account_statement: period_from field filled")
            except Exception as e:
                self.logger.warning(
                    "connector.get_account_statement: period_from field not found",
                    selector=selector,
                    error=str(e)
                )

            try:
                selector = 'input[name="perhasta2"]'
                self.logger.info(
                    "connector.get_account_statement: filling period_to field",
                    selector=selector,
                    value=period_to
                )
                await account_page.fill(selector, period_to)
                self.logger.info("connector.get_account_statement: period_to field filled")
            except Exception as e:
                self.logger.warning(
                    "connector.get_account_statement: period_to field not found",
                    selector=selector,
                    error=str(e)
                )

            try:
                selector = 'input[name="feccalculo"]'
                self.logger.info(
                    "connector.get_account_statement: filling calculation_date field",
                    selector=selector,
                    value=calculation_date
                )
                await account_page.fill(selector, calculation_date)
                self.logger.info("connector.get_account_statement: calculation_date field filled")
            except Exception as e:
                self.logger.warning(
                    "connector.get_account_statement: calculation_date field not found",
                    selector=selector,
                    error=str(e)
                )

            # ------------------------------------------------------------------
            # Step 4 – click **Cálculo de deuda**
            # ------------------------------------------------------------------
            self.logger.info("connector.get_account_statement: looking for Cálculo de deuda button")

            # The button is: <input type="button" name="CalDeud" value="CALCULO DE DEUDA">
            calculo_selectors = [
                'input[name="CalDeud"]',
                'input[value="CALCULO DE DEUDA"]',
                'input[type="button"][value*="CALCULO"]',
            ]

            button_clicked = False
            for sel in calculo_selectors:
                try:
                    self.logger.info(
                        "connector.get_account_statement: trying selector",
                        selector=sel
                    )
                    await account_page.click(sel, timeout=5_000)
                    button_clicked = True
                    self.logger.info(
                        "connector.get_account_statement: Cálculo button clicked",
                        selector=sel
                    )
                    break
                except Exception as e:
                    self.logger.debug(
                        "connector.get_account_statement: selector failed",
                        selector=sel,
                        error=str(e)
                    )
                    continue
            
            if not button_clicked:
                self.logger.error("connector.get_account_statement: Cálculo de deuda button not found")
                return None

            self.logger.info("connector.get_account_statement: waiting for calculation to complete")
            await asyncio.sleep(5)

            # Debug: Save HTML after calculation
            if os.getenv("AFIP_DEBUG", "false").lower() == "true":
                debug_path = "/tmp/afip_account_page_after_calc.html"
                self.logger.info(
                    "connector.get_account_statement: saving debug HTML after calculation",
                    path=debug_path
                )
                html = await account_page.content()
                with open(debug_path, "w") as f:
                    f.write(html)
                self.logger.info(
                    "connector.get_account_statement: debug HTML saved after calculation",
                    path=debug_path,
                    size=len(html)
                )
            
            # Give extra time for JavaScript rendering
            self.logger.info("connector.get_account_statement: waiting for JavaScript rendering")
            await asyncio.sleep(2)

            # ------------------------------------------------------------------
            # Step 5 – screenshot
            # ------------------------------------------------------------------
            screenshots_dir = Path("/tmp/afip_screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot_path = screenshots_dir / f"estado_cuenta_{self._current_session.cuit}_{ts}.png"
            
            self.logger.info(
                "connector.get_account_statement: taking screenshot",
                path=str(shot_path)
            )
            await account_page.screenshot(path=str(shot_path), full_page=True)
            self.logger.info(
                "connector.get_account_statement: screenshot saved",
                path=str(shot_path),
                cuit=self._current_session.cuit
            )

            # ------------------------------------------------------------------
            # Step 6 – parse “Total Saldo Deudor”
            # ------------------------------------------------------------------
            self.logger.info("connector.get_account_statement: starting data extraction")
            
            # Debug mode: save what we're seeing
            if os.getenv("AFIP_DEBUG", "false").lower() == "true":
                try:
                    debug_path = "/tmp/afip_innertext.txt"
                    self.logger.info(
                        "connector.get_account_statement: extracting page text for debug",
                        path=debug_path
                    )
                    debug_text = await account_page.evaluate("document.body.innerText")
                    with open(debug_path, "w") as f:
                        f.write(str(debug_text))
                    self.logger.info(
                        "connector.get_account_statement: debug text saved",
                        path=debug_path,
                        size=len(str(debug_text))
                    )
                except Exception as e:
                    self.logger.warning(
                        "connector.get_account_statement: debug text extraction error",
                        error=str(e)
                    )
            
            self.logger.info("connector.get_account_statement: executing JavaScript to find Total Saldo Deudor")
            debt_text = await account_page.evaluate(
                """return (() => {
                     // Get all table cells
                     const cells = document.getElementsByTagName('td');
                     
                     // Find the cell with "Total Saldo Deudor"
                     for (let i = 0; i < cells.length; i++) {
                         const cell = cells[i];
                         const text = cell.textContent || cell.innerText || '';
                         
                         if (text.includes('Total Saldo Deudor')) {
                             // Look at the parent row and find the table containing the value
                             const row = cell.parentElement;
                             if (!row) continue;
                             
                             // Find all nested tables in this row
                             const tables = row.getElementsByTagName('table');
                             
                             // The value is typically in a small table that only contains the number
                             for (let table of tables) {
                                 const tableText = (table.textContent || table.innerText || '').trim();
                                 // Check if this table contains only a number in the expected format
                                 if (/^[0-9]{1,3}(,[0-9]{3})*\\.[0-9]{2}$/.test(tableText)) {
                                     return tableText;
                                 }
                             }
                         }
                     }
                     
                     // If not found, return null
                     return null;
                 })()"""
            )

            if debt_text:
                self.logger.info(
                    "connector.get_account_statement: debt text found",
                    raw_text=debt_text
                )
                # Handle format like 236,701.14 (comma as thousand separator, period as decimal)
                amount = float(debt_text.replace(",", ""))
                self.logger.info(
                    "connector.get_account_statement: debt amount parsed",
                    raw_text=debt_text,
                    parsed_amount=amount
                )
            else:
                self.logger.warning("connector.get_account_statement: Total Saldo Deudor not found in page")
                amount = 0.0

            stmt = AccountStatement(
                total_debt=amount,
                screenshot_path=str(shot_path),
                period_from=period_from,
                period_to=period_to,
                calculation_date=calculation_date,
                retrieved_at=datetime.now(),
            )

            self.logger.info(
                "connector.get_account_statement: account statement retrieved successfully",
                total_debt=amount,
                screenshot=str(shot_path),
                period_from=period_from,
                period_to=period_to,
                calculation_date=calculation_date,
                cuit=self._current_session.cuit
            )
            return stmt

        except Exception as exc:
            self.logger.error(
                "connector.get_account_statement: error occurred",
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True
            )
            return None
