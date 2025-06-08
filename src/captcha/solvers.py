"""Implementaciones de solvers de captcha."""

import asyncio
import base64
from typing import Any, Dict, Optional

import structlog

from src.browser.interfaces import IPage
from src.connectors.afip.interfaces import ICaptchaSolver

logger = structlog.get_logger()


class CapSolverAI(ICaptchaSolver):
    """Solver usando CapSolver AI."""
    
    def __init__(self, api_key: str):
        """Inicializa el solver.
        
        Args:
            api_key: API key de CapSolver.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="CapSolverAI")
        # En producción, esto usaría el cliente HTTP real de CapSolver
        self.base_url = "https://api.capsolver.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Verifica si puede manejar el tipo de captcha.
        
        Args:
            captcha_type: Tipo de captcha.
            
        Returns:
            True si puede manejarlo.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "image"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Resuelve el captcha usando CapSolver.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            Solución del captcha o None.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                # Para captchas de imagen
                image_selector = captcha_info.get("image_selector", "img.captcha")
                
                # Obtener la imagen del captcha
                image_base64 = await page.evaluate(f"""
                    () => {{
                        const img = document.querySelector('{image_selector}');
                        if (!img) return null;
                        
                        const canvas = document.createElement('canvas');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0);
                        return canvas.toDataURL('image/png').split(',')[1];
                    }}
                """)
                
                if not image_base64:
                    self.logger.error("captcha_image_not_found")
                    return None
                
                # Aquí iría la llamada real a la API de CapSolver
                # Por ahora, simulamos una respuesta
                self.logger.info("sending_captcha_to_capsolver")
                await asyncio.sleep(2)  # Simular delay de API
                
                # En producción, esto sería la respuesta real de CapSolver
                return "SIMULATED_CAPTCHA_SOLUTION"
            
            elif captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                site_key = captcha_info.get("site_key")
                if not site_key:
                    self.logger.error("recaptcha_site_key_missing")
                    return None
                
                # Aquí iría la integración con CapSolver para ReCaptcha
                self.logger.info(
                    "solving_recaptcha",
                    type=captcha_type,
                    site_key=site_key
                )
                await asyncio.sleep(3)  # Simular delay
                
                return "SIMULATED_RECAPTCHA_TOKEN"
            
            else:
                self.logger.warning("unsupported_captcha_type", type=captcha_type)
                return None
                
        except Exception as e:
            self.logger.error(
                "capsolver_error",
                error=str(e),
                exc_info=True
            )
            raise


class TwoCaptchaSolver(ICaptchaSolver):
    """Solver usando 2Captcha."""
    
    def __init__(self, api_key: str):
        """Inicializa el solver.
        
        Args:
            api_key: API key de 2Captcha.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="2Captcha")
        self.base_url = "https://2captcha.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Verifica si puede manejar el tipo de captcha.
        
        Args:
            captcha_type: Tipo de captcha.
            
        Returns:
            True si puede manejarlo.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "image", "text"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Resuelve el captcha usando 2Captcha.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            Solución del captcha o None.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                image_selector = captcha_info.get("image_selector", "img.captcha")
                
                # Capturar screenshot del captcha
                screenshot_path = f"/tmp/captcha_{id(self)}.png"
                await page.screenshot(screenshot_path)
                
                # En producción, enviaríamos la imagen a 2Captcha
                self.logger.info("sending_captcha_to_2captcha")
                await asyncio.sleep(2.5)  # Simular delay
                
                return "SIMULATED_2CAPTCHA_SOLUTION"
            
            elif captcha_type == "text":
                # Para captchas de texto simple
                question = captcha_info.get("question", "")
                self.logger.info("solving_text_captcha", question=question)
                await asyncio.sleep(1.5)
                
                return "SIMULATED_TEXT_ANSWER"
            
            elif captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                site_key = captcha_info.get("site_key")
                page_url = await page.evaluate("() => window.location.href")
                
                if not site_key:
                    self.logger.error("recaptcha_site_key_missing")
                    return None
                
                self.logger.info(
                    "solving_recaptcha_with_2captcha",
                    type=captcha_type,
                    site_key=site_key,
                    url=page_url
                )
                await asyncio.sleep(4)  # 2Captcha suele tardar más
                
                return "SIMULATED_2CAPTCHA_RECAPTCHA_TOKEN"
            
            else:
                self.logger.warning("unsupported_captcha_type", type=captcha_type)
                return None
                
        except Exception as e:
            self.logger.error(
                "twocaptcha_error",
                error=str(e),
                exc_info=True
            )
            raise


class AntiCaptchaSolver(ICaptchaSolver):
    """Solver usando Anti-Captcha."""
    
    def __init__(self, api_key: str):
        """Inicializa el solver.
        
        Args:
            api_key: API key de Anti-Captcha.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="AntiCaptcha")
        self.base_url = "https://api.anti-captcha.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Verifica si puede manejar el tipo de captcha.
        
        Args:
            captcha_type: Tipo de captcha.
            
        Returns:
            True si puede manejarlo.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "funcaptcha", "image"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Resuelve el captcha usando Anti-Captcha.
        
        Args:
            page: Página con el captcha.
            captcha_info: Información del captcha.
            
        Returns:
            Solución del captcha o None.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                # Similar a los otros solvers
                self.logger.info("solving_image_captcha_with_anticaptcha")
                await asyncio.sleep(2)
                return "SIMULATED_ANTICAPTCHA_SOLUTION"
            
            elif captcha_type == "funcaptcha":
                # FunCaptcha es especial de Anti-Captcha
                public_key = captcha_info.get("public_key")
                if not public_key:
                    self.logger.error("funcaptcha_public_key_missing")
                    return None
                
                self.logger.info("solving_funcaptcha", public_key=public_key)
                await asyncio.sleep(3.5)
                return "SIMULATED_FUNCAPTCHA_TOKEN"
            
            elif captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                site_key = captcha_info.get("site_key")
                if not site_key:
                    return None
                
                self.logger.info("solving_recaptcha_with_anticaptcha", type=captcha_type)
                await asyncio.sleep(3)
                return "SIMULATED_ANTICAPTCHA_RECAPTCHA_TOKEN"
            
            else:
                return None
                
        except Exception as e:
            self.logger.error(
                "anticaptcha_error",
                error=str(e),
                exc_info=True
            )
            raise