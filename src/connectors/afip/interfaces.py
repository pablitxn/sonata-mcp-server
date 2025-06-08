"""Interfaces para el connector de AFIP."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LoginStatus(Enum):
    """Estado del login en AFIP."""
    SUCCESS = "success"
    FAILED = "failed"
    CAPTCHA_REQUIRED = "captcha_required"
    CERTIFICATE_REQUIRED = "certificate_required"
    SESSION_EXPIRED = "session_expired"


class PaymentStatus(Enum):
    """Estado de un pago."""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"


@dataclass
class AFIPCredentials:
    """Credenciales para login en AFIP."""
    cuit: str
    password: str
    certificate_path: Optional[str] = None
    certificate_password: Optional[str] = None


@dataclass
class AFIPSession:
    """Información de sesión de AFIP."""
    session_id: str
    cuit: str
    cookies: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    is_valid: bool = True


@dataclass
class Payment:
    """Información de un pago pendiente."""
    id: str
    description: str
    amount: float
    due_date: datetime
    status: PaymentStatus
    tax_type: str
    period: str


class IAFIPConnector(ABC):
    """Interfaz principal del connector de AFIP."""
    
    @abstractmethod
    async def login(self, credentials: AFIPCredentials) -> LoginStatus:
        """Inicia sesión en AFIP.
        
        Args:
            credentials: Credenciales de acceso.
            
        Returns:
            Estado del login.
        """
        pass
    
    @abstractmethod
    async def logout(self) -> bool:
        """Cierra la sesión actual.
        
        Returns:
            True si se cerró correctamente.
        """
        pass
    
    @abstractmethod
    async def get_pending_payments(self) -> List[Payment]:
        """Obtiene la lista de pagos pendientes.
        
        Returns:
            Lista de pagos pendientes.
        """
        pass
    
    @abstractmethod
    async def get_session(self) -> Optional[AFIPSession]:
        """Obtiene la sesión actual.
        
        Returns:
            Información de la sesión o None si no hay sesión activa.
        """
        pass
    
    @abstractmethod
    async def restore_session(self, session: AFIPSession) -> bool:
        """Restaura una sesión previamente guardada.
        
        Args:
            session: Sesión a restaurar.
            
        Returns:
            True si se restauró correctamente.
        """
        pass



class ISessionStorage(ABC):
    """Interfaz para almacenamiento de sesiones."""
    
    @abstractmethod
    async def save(self, session: AFIPSession) -> bool:
        """Guarda una sesión.
        
        Args:
            session: Sesión a guardar.
            
        Returns:
            True si se guardó correctamente.
        """
        pass
    
    @abstractmethod
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Carga una sesión guardada.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            Sesión guardada o None si no existe.
        """
        pass
    
    @abstractmethod
    async def delete(self, cuit: str) -> bool:
        """Elimina una sesión guardada.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            True si se eliminó correctamente.
        """
        pass
    
    @abstractmethod
    async def is_valid(self, session: AFIPSession) -> bool:
        """Verifica si una sesión es válida.
        
        Args:
            session: Sesión a verificar.
            
        Returns:
            True si la sesión es válida.
        """
        pass