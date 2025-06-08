"""Implementación del connector de AFIP."""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

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

logger = structlog.get_logger()


class AFIPConnector(IAFIPConnector):
    """Conector para interactuar con AFIP."""

    # URLs de AFIP
    LOGIN_URL = "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
    DASHBOARD_URL = "https://portalcf.cloud.afip.gob.ar/portal/app/"
    PAYMENTS_URL = "https://portalcf.cloud.afip.gob.ar/portal/app/consultaDeuda"

    def __init__(
            self,
            browser_factory: BrowserEngineFactory,
            session_storage: Optional[ISessionStorage] = None,
            captcha_chain: Optional[CaptchaChain] = None,
            browser_config: Optional[BrowserConfig] = None
    ):
        """Inicializa el connector.
        
        Args:
            browser_factory: Factory para crear instancias de browser.
            session_storage: Almacenamiento de sesiones (opcional).
            captcha_chain: Cadena de resolvedores de captcha (opcional).
            browser_config: Configuración del browser (opcional).
        """
        self.browser_factory = browser_factory
        self.session_storage = session_storage or EncryptedSessionStorage("/tmp/afip_sessions")
        self.captcha_chain = captcha_chain or self._create_default_captcha_chain()
        self.browser_config = browser_config or BrowserConfig(
            headless=False,  # AFIP suele detectar headless
            viewport={"width": 1280, "height": 720}
        )

        self._context: Optional[IBrowserContext] = None
        self._page: Optional[IPage] = None
        self._current_session: Optional[AFIPSession] = None

        self.logger = logger.bind(connector="afip")

    def _create_default_captcha_chain(self) -> CaptchaChain:
        """Crea la cadena de captcha por defecto.
        
        Returns:
            Cadena configurada con solvers.
        """
        chain = CaptchaChain()

        # Configuración más agresiva para el circuit breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=timedelta(minutes=5),
            success_threshold=2
        )

        # Agregar solvers en orden de preferencia
        # Nota: En producción, estas API keys vendrían de configuración
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
        """Inicializa el browser y contexto."""
        if not self._context:
            # Usar selenium como engine por defecto
            from src.browser.interfaces import BrowserType
            engine = await self.browser_factory.create(
                BrowserType.SELENIUM,
                self.browser_config
            )

            self._context = await engine.create_context({
                "accept_downloads": False,
                "bypass_csp": True,
                "java_script_enabled": True
            })

            self._page = await self._context.new_page()
            self.logger.info("browser_initialized")

    async def _detect_captcha(self, page: IPage) -> Optional[Dict[str, Any]]:
        """Detecta si hay un captcha en la página.
        
        Args:
            page: Página a verificar.
            
        Returns:
            Información del captcha o None.
        """
        try:
            # Verificar diferentes tipos de captcha que usa AFIP

            # Captcha de imagen
            has_image_captcha = await page.evaluate("""
                () => {
                    const captcha = document.querySelector('img[id*="captcha"], img[src*="captcha"]');
                    return captcha !== null;
                }
            """)

            if has_image_captcha:
                return {
                    "type": "image",
                    "image_selector": 'img[id*="captcha"], img[src*="captcha"]',
                    "input_selector": 'input[id*="captcha"], input[name*="captcha"]'
                }

            # ReCaptcha
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
                    "site_key": site_key
                }

            return None

        except Exception as e:
            self.logger.error("captcha_detection_error", error=str(e))
            return None

    async def _solve_captcha(self, page: IPage, captcha_info: Dict[str, Any]) -> bool:
        """Intenta resolver un captcha.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            True si se resolvió correctamente.
        """
        try:
            solution = await self.captcha_chain.solve(page, captcha_info)

            if not solution:
                self.logger.error("captcha_not_solved")
                return False

            # Aplicar la solución según el tipo
            if captcha_info["type"] == "image":
                input_selector = captcha_info.get("input_selector")
                await page.fill(input_selector, solution)
                self.logger.info("captcha_solution_filled")

            elif captcha_info["type"] == "recaptcha_v2":
                # Inyectar el token de ReCaptcha
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
        """Inicia sesión en AFIP.
        
        Args:
            credentials: Credenciales de acceso.
            
        Returns:
            Estado del login.
        """
        try:
            # Intentar restaurar sesión guardada
            if self.session_storage:
                saved_session = await self.session_storage.load(credentials.cuit)
                if saved_session and await self.session_storage.is_valid(saved_session):
                    if await self.restore_session(saved_session):
                        self.logger.info("session_restored", cuit=credentials.cuit)
                        return LoginStatus.SUCCESS

            # Inicializar browser
            await self._initialize_browser()

            # Navegar a la página de login
            self.logger.info("navigating_to_login")
            await self._page.goto(self.LOGIN_URL, wait_until="networkidle")

            # Esperar que cargue el formulario
            await self._page.wait_for_selector('input[name="user"]', timeout=10000)

            # Completar credenciales
            await self._page.fill('input[name="user"]', credentials.cuit)
            await self._page.fill('input[name="password"]', credentials.password)

            # Verificar si hay captcha
            captcha_info = await self._detect_captcha(self._page)
            if captcha_info:
                self.logger.info("captcha_detected", type=captcha_info["type"])

                if not await self._solve_captcha(self._page, captcha_info):
                    return LoginStatus.CAPTCHA_REQUIRED

            # Hacer click en login
            await self._page.click('button[type="submit"], input[type="submit"]')

            # Esperar navegación
            try:
                await self._page.wait_for_selector(
                    'a[href*="logout"], button[id*="logout"]',
                    timeout=15000
                )

                # Login exitoso, guardar sesión
                cookies = await self._context.get_cookies()

                self._current_session = AFIPSession(
                    session_id=f"afip_{credentials.cuit}_{datetime.now().timestamp()}",
                    cuit=credentials.cuit,
                    cookies={c["name"]: c["value"] for c in cookies},
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=2),  # AFIP sessions típicamente 2h
                    is_valid=True
                )

                # Guardar sesión
                if self.session_storage:
                    await self.session_storage.save(self._current_session)

                self.logger.info("login_successful", cuit=credentials.cuit)
                return LoginStatus.SUCCESS

            except Exception:
                # Verificar si requiere certificado
                requires_cert = await self._page.evaluate("""
                    () => {
                        const text = document.body.innerText.toLowerCase();
                        return text.includes('certificado') || text.includes('certificate');
                    }
                """)

                if requires_cert:
                    return LoginStatus.CERTIFICATE_REQUIRED

                return LoginStatus.FAILED

        except Exception as e:
            self.logger.error("login_error", error=str(e), exc_info=True)
            return LoginStatus.FAILED

    async def logout(self) -> bool:
        """Cierra la sesión actual.
        
        Returns:
            True si se cerró correctamente.
        """
        try:
            if not self._page:
                return True

            # Buscar y hacer click en logout
            logout_selectors = [
                'a[href*="logout"]',
                'button[id*="logout"]',
                'a:has-text("Salir")',
                'button:has-text("Cerrar sesión")'
            ]

            for selector in logout_selectors:
                try:
                    await self._page.click(selector, timeout=5000)
                    break
                except:
                    continue

            # Invalidar sesión guardada
            if self._current_session and self.session_storage:
                await self.session_storage.delete(self._current_session.cuit)

            self._current_session = None

            # Cerrar browser
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
        """Obtiene la lista de pagos pendientes.
        
        Returns:
            Lista de pagos pendientes.
        """
        try:
            if not self._current_session:
                self.logger.error("no_active_session")
                return []

            # Navegar a la página de pagos
            self.logger.info("navigating_to_payments")
            await self._page.goto(self.PAYMENTS_URL, wait_until="networkidle")

            # Esperar que cargue la tabla de pagos
            await self._page.wait_for_selector('table[id*="deuda"], .tabla-deudas', timeout=15000)

            # Extraer información de pagos
            payments_data = await self._page.evaluate("""
                () => {
                    const payments = [];
                    const rows = document.querySelectorAll('table[id*="deuda"] tr, .tabla-deudas tr');
                    
                    for (let i = 1; i < rows.length; i++) {  // Skip header
                        const cells = rows[i].querySelectorAll('td');
                        if (cells.length >= 5) {
                            payments.push({
                                id: cells[0].innerText.trim(),
                                description: cells[1].innerText.trim(),
                                amount: cells[2].innerText.trim(),
                                due_date: cells[3].innerText.trim(),
                                status: cells[4].innerText.trim(),
                                tax_type: cells[5] ? cells[5].innerText.trim() : '',
                                period: cells[6] ? cells[6].innerText.trim() : ''
                            });
                        }
                    }
                    
                    return payments;
                }
            """)

            # Convertir a objetos Payment
            payments = []
            for data in payments_data:
                try:
                    # Parsear monto (remover símbolos de moneda)
                    # Formato argentino: $10.500,50 -> 10500.50
                    amount_str = data["amount"].replace("$", "").replace(".", "")
                    amount_str = amount_str.replace(",", ".")
                    amount = float(amount_str)

                    # Parsear fecha
                    due_date = datetime.strptime(data["due_date"], "%d/%m/%Y")

                    # Determinar estado
                    status_map = {
                        "pendiente": PaymentStatus.PENDING,
                        "vencido": PaymentStatus.OVERDUE,
                        "pagado": PaymentStatus.PAID,
                        "parcial": PaymentStatus.PARTIAL
                    }
                    status = status_map.get(
                        data["status"].lower(),
                        PaymentStatus.PENDING
                    )

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
        """Obtiene la sesión actual.
        
        Returns:
            Información de la sesión o None.
        """
        return self._current_session

    async def restore_session(self, session: AFIPSession) -> bool:
        """Restaura una sesión previamente guardada.
        
        Args:
            session: Sesión a restaurar.
            
        Returns:
            True si se restauró correctamente.
        """
        try:
            # Verificar validez
            if not await self.session_storage.is_valid(session):
                self.logger.warning("session_invalid_for_restore", cuit=session.cuit)
                return False

            # Inicializar browser
            await self._initialize_browser()

            # Navegar a AFIP
            await self._page.goto(self.LOGIN_URL)

            # Establecer cookies
            cookies_list = [
                {
                    "name": name,
                    "value": value,
                    "domain": ".afip.gob.ar",
                    "path": "/"
                }
                for name, value in session.cookies.items()
            ]
            await self._context.set_cookies(cookies_list)

            # Navegar al dashboard para verificar
            await self._page.goto(self.DASHBOARD_URL)

            # Verificar si la sesión es válida
            is_logged_in = await self._page.evaluate("""
                () => {
                    return document.querySelector('a[href*="logout"], button[id*="logout"]') !== null;
                }
            """)

            if is_logged_in:
                self._current_session = session
                self.logger.info("session_restored_successfully", cuit=session.cuit)
                return True
            else:
                self.logger.warning("session_restore_failed", cuit=session.cuit)
                return False

        except Exception as e:
            self.logger.error(
                "session_restore_error",
                error=str(e),
                exc_info=True
            )
            return False
