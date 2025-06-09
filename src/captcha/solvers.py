"""Captcha solver implementations.

This module contains concrete implementations of the ICaptchaSolver interface
for various captcha solving services. Each solver is designed to handle specific
types of captchas and communicate with their respective APIs.

Note: The current implementations are mocked for testing purposes.
In production, these would integrate with actual captcha solving services.
"""

import asyncio
import base64
from typing import Any, Dict, Optional

from browser.interfaces import IPage
from config.mcp_logger import logger
from .interfaces import ICaptchaSolver


class CapSolverAI(ICaptchaSolver):
    """Captcha solver using CapSolver AI service.
    
    CapSolver is a modern captcha solving service that supports various
    captcha types including ReCaptcha, hCaptcha, and image-based captchas.
    It uses AI-powered solutions for high accuracy and speed.
    """
    
    def __init__(self, api_key: str):
        """Initialize the CapSolver solver.
        
        Args:
            api_key: CapSolver API key for authentication.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="CapSolverAI")
        # In production, this would use the actual CapSolver HTTP client
        self.base_url = "https://api.capsolver.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Check if CapSolver can handle the given captcha type.
        
        Args:
            captcha_type: Type of captcha to check.
            
        Returns:
            True if the captcha type is supported.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "image"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Solve the captcha using CapSolver API.
        
        This method handles different captcha types and communicates with
        the CapSolver service to obtain solutions.
        
        Args:
            page: Page interface containing the captcha.
            captcha_info: Dictionary with captcha details.
            
        Returns:
            The captcha solution or None if unable to solve.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                # Handle image-based captchas
                image_selector = captcha_info.get("image_selector", "img.captcha")
                
                # Extract captcha image from the page
                image_base64 = await page.evaluate(f"""
                    () => {{
                        const img = document.querySelector('{image_selector}');
                        if (!img) return null;
                        
                        // Convert image to base64 using canvas
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
                
                # In production, this would make an actual API call to CapSolver
                # Currently simulating the API interaction
                self.logger.info("sending_captcha_to_capsolver")
                await asyncio.sleep(2)  # Simulate API delay
                
                # In production, this would be the actual CapSolver response
                return "SIMULATED_CAPTCHA_SOLUTION"
            
            elif captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                site_key = captcha_info.get("site_key")
                if not site_key:
                    self.logger.error("recaptcha_site_key_missing")
                    return None
                
                # In production, this would integrate with CapSolver's ReCaptcha solving
                self.logger.info(
                    "solving_recaptcha",
                    type=captcha_type,
                    site_key=site_key
                )
                await asyncio.sleep(3)  # Simulate processing delay
                
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
    """Captcha solver using 2Captcha service.
    
    2Captcha is one of the oldest and most reliable captcha solving services.
    It supports a wide range of captcha types and has both automated and
    human-powered solving capabilities.
    """
    
    def __init__(self, api_key: str):
        """Initialize the 2Captcha solver.
        
        Args:
            api_key: 2Captcha API key for authentication.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="2Captcha")
        self.base_url = "https://2captcha.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Check if 2Captcha can handle the given captcha type.
        
        2Captcha supports the widest range of captcha types.
        
        Args:
            captcha_type: Type of captcha to check.
            
        Returns:
            True if the captcha type is supported.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "image", "text"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Solve the captcha using 2Captcha API.
        
        2Captcha uses a combination of AI and human workers to solve captchas,
        which can result in longer solving times but higher accuracy.
        
        Args:
            page: Page interface containing the captcha.
            captcha_info: Dictionary with captcha details.
            
        Returns:
            The captcha solution or None if unable to solve.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                image_selector = captcha_info.get("image_selector", "img.captcha")
                
                # Capture screenshot of the captcha for processing
                screenshot_path = f"/tmp/captcha_{id(self)}.png"
                await page.screenshot(screenshot_path)
                
                # In production, we would send the image to 2Captcha API
                self.logger.info("sending_captcha_to_2captcha")
                await asyncio.sleep(2.5)  # Simulate API delay
                
                return "SIMULATED_2CAPTCHA_SOLUTION"
            
            elif captcha_type == "text":
                # Handle simple text-based captchas (e.g., "What is 2+2?")
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
                await asyncio.sleep(4)  # 2Captcha typically takes longer
                
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
    """Captcha solver using Anti-Captcha service.
    
    Anti-Captcha is known for its competitive pricing and good support
    for modern captcha types like FunCaptcha. It provides both API and
    browser plugin solutions.
    """
    
    def __init__(self, api_key: str):
        """Initialize the Anti-Captcha solver.
        
        Args:
            api_key: Anti-Captcha API key for authentication.
        """
        self.api_key = api_key
        self.logger = logger.bind(solver="AntiCaptcha")
        self.base_url = "https://api.anti-captcha.com"
    
    def can_handle(self, captcha_type: str) -> bool:
        """Check if Anti-Captcha can handle the given captcha type.
        
        Anti-Captcha specializes in certain captcha types, particularly FunCaptcha.
        
        Args:
            captcha_type: Type of captcha to check.
            
        Returns:
            True if the captcha type is supported.
        """
        supported_types = ["recaptcha_v2", "recaptcha_v3", "funcaptcha", "image"]
        return captcha_type.lower() in supported_types
    
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Solve the captcha using Anti-Captcha API.
        
        Anti-Captcha is particularly effective with FunCaptcha challenges
        and provides good performance for ReCaptcha as well.
        
        Args:
            page: Page interface containing the captcha.
            captcha_info: Dictionary with captcha details.
            
        Returns:
            The captcha solution or None if unable to solve.
        """
        try:
            captcha_type = captcha_info.get("type", "")
            
            if captcha_type == "image":
                # Similar approach to other solvers for image captchas
                self.logger.info("solving_image_captcha_with_anticaptcha")
                await asyncio.sleep(2)
                return "SIMULATED_ANTICAPTCHA_SOLUTION"
            
            elif captcha_type == "funcaptcha":
                # FunCaptcha is a specialty of Anti-Captcha
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