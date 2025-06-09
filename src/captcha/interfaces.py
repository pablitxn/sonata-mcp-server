"""Interfaces for the captcha system.

This module defines the core interfaces that all captcha solver implementations must follow.
The interface provides a consistent API for different captcha solving services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.browser.interfaces import IPage


class ICaptchaSolver(ABC):
    """Interface for captcha solvers.
    
    All captcha solver implementations must inherit from this interface
    and implement the required methods. This ensures consistency across
    different captcha solving services (CapSolver, 2Captcha, AntiCaptcha, etc.).
    """
    
    @abstractmethod
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Solve a captcha challenge.
        
        This method should handle the complete captcha solving process,
        including extracting necessary information from the page,
        communicating with the solving service, and returning the solution.
        
        Args:
            page: The page interface where the captcha is located.
            captcha_info: Dictionary containing captcha details such as:
                - type: The captcha type (e.g., 'recaptcha_v2', 'hcaptcha', 'image')
                - selector: CSS selector for the captcha element (if applicable)
                - sitekey: The site key for ReCaptcha/hCaptcha (if applicable)
                - image_url: URL of the image captcha (if applicable)
                - Additional service-specific parameters
            
        Returns:
            The captcha solution string if successful, None if unable to solve.
            The solution format depends on the captcha type:
            - For ReCaptcha/hCaptcha: The response token
            - For image captcha: The text shown in the image
            - For other types: Service-specific solution format
        """
        pass
    
    @abstractmethod
    def can_handle(self, captcha_type: str) -> bool:
        """Check if this solver can handle a specific captcha type.
        
        This method is used by the chain of responsibility to determine
        which solver should attempt to solve a given captcha.
        
        Args:
            captcha_type: The type of captcha to check. Common types include:
                - 'recaptcha_v2': Google ReCaptcha v2
                - 'recaptcha_v3': Google ReCaptcha v3
                - 'hcaptcha': hCaptcha challenges
                - 'funcaptcha': Arkose Labs FunCaptcha
                - 'image': Image-based text captcha
                - 'text': Simple text-based captcha
            
        Returns:
            True if this solver supports the given captcha type, False otherwise.
        """
        pass