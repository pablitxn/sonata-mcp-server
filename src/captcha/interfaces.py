"""Interfaces para el sistema de captcha."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.browser.interfaces import IPage


class ICaptchaSolver(ABC):
    """Interfaz para resolvedores de captcha."""
    
    @abstractmethod
    async def solve(self, page: IPage, captcha_info: Dict[str, Any]) -> Optional[str]:
        """Resuelve un captcha.
        
        Args:
            page: Página donde está el captcha.
            captcha_info: Información del captcha (selector, tipo, etc).
            
        Returns:
            Solución del captcha o None si no pudo resolverlo.
        """
        pass
    
    @abstractmethod
    def can_handle(self, captcha_type: str) -> bool:
        """Verifica si puede manejar este tipo de captcha.
        
        Args:
            captcha_type: Tipo de captcha.
            
        Returns:
            True si puede manejarlo.
        """
        pass