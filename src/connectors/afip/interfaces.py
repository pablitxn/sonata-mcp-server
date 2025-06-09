"""Interfaces for the AFIP connector.

This module defines the core interfaces and data structures used by the AFIP connector.
It provides type safety through dataclasses and enums, ensuring consistent data handling
throughout the connector implementation.

AFIP (Administración Federal de Ingresos Públicos) is Argentina's federal tax agency,
and these interfaces facilitate automated interaction with their web services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LoginStatus(Enum):
    """Login status enumeration for AFIP authentication.
    
    Represents the various states that can result from a login attempt,
    helping to handle different scenarios appropriately.
    """
    SUCCESS = "success"  # Login completed successfully
    FAILED = "failed"  # Login failed due to invalid credentials
    CAPTCHA_REQUIRED = "captcha_required"  # Login requires captcha solving
    CERTIFICATE_REQUIRED = "certificate_required"  # Digital certificate authentication needed
    SESSION_EXPIRED = "session_expired"  # Previous session has expired


class PaymentStatus(Enum):
    """Payment status enumeration.
    
    Represents the different states a tax payment obligation can have
    in the AFIP system.
    """
    PENDING = "pending"  # Payment is due but not yet paid
    PAID = "paid"  # Payment has been completed
    OVERDUE = "overdue"  # Payment is past its due date
    PARTIAL = "partial"  # Partial payment has been made


@dataclass
class AFIPCredentials:
    """Credentials for AFIP authentication.
    
    Contains all necessary information for authenticating with AFIP services.
    Supports both password-based and certificate-based authentication methods.
    
    Attributes:
        cuit: Tax identification number (Clave Única de Identificación Tributaria).
              Must be a valid 11-digit number without hyphens.
        password: Account password for authentication.
        certificate_path: Optional path to digital certificate file (.pfx/.p12).
        certificate_password: Optional password for the digital certificate.
    """
    cuit: str
    password: str
    certificate_path: Optional[str] = None
    certificate_password: Optional[str] = None


@dataclass
class AFIPSession:
    """AFIP session information.
    
    Represents an active session with AFIP services. Sessions can be persisted
    and restored to avoid repeated logins and captcha solving.
    
    Attributes:
        session_id: Unique identifier for the session.
        cuit: Tax ID associated with this session.
        cookies: Browser cookies maintaining the session state.
        created_at: Timestamp when the session was created.
        expires_at: Timestamp when the session will expire.
        is_valid: Whether the session is still valid for use.
    """
    session_id: str
    cuit: str
    cookies: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    is_valid: bool = True


@dataclass
class Payment:
    """Tax payment obligation information.
    
    Represents a single tax payment obligation retrieved from AFIP,
    containing all relevant details for identification and processing.
    
    Attributes:
        id: Unique identifier for the payment obligation.
        description: Human-readable description of the tax obligation.
        amount: Amount due in Argentine pesos (ARS).
        due_date: Date by which the payment must be made.
        status: Current status of the payment.
        tax_type: Type of tax (e.g., 'IVA', 'Ganancias', etc.).
        period: Tax period this payment corresponds to (e.g., '2024-03').
    """
    id: str
    description: str
    amount: float
    due_date: datetime
    status: PaymentStatus
    tax_type: str
    period: str


@dataclass
class AccountStatement:
    """Account statement information from AFIP.
    
    Represents the account statement data including total debt amount
    and a screenshot of the statement page.
    
    Attributes:
        total_debt: Total debt amount in Argentine pesos (ARS).
        screenshot_path: Path to the saved screenshot file.
        period_from: Start period for the statement (MM/YYYY format).
        period_to: End period for the statement (MM/YYYY format).
        calculation_date: Date when the calculation was performed.
        retrieved_at: Timestamp when the data was retrieved.
    """
    total_debt: float
    screenshot_path: str
    period_from: str
    period_to: str
    calculation_date: str
    retrieved_at: datetime


class IAFIPConnector(ABC):
    """Main interface for the AFIP connector.
    
    Defines the contract that all AFIP connector implementations must follow.
    This interface ensures consistent behavior across different implementations
    and facilitates testing through dependency injection.
    """
    
    @abstractmethod
    async def login(self, credentials: AFIPCredentials) -> LoginStatus:
        """Authenticate with AFIP services.
        
        Performs login to AFIP using the provided credentials. Handles various
        authentication scenarios including captcha challenges and certificate
        requirements.
        
        Args:
            credentials: Authentication credentials containing CUIT and password.
            
        Returns:
            LoginStatus indicating the result of the authentication attempt.
            
        Raises:
            Exception: If there's a network or browser automation error.
        """
        pass
    
    @abstractmethod
    async def logout(self) -> bool:
        """Close the current AFIP session.
        
        Properly logs out from AFIP services and cleans up browser resources.
        Also invalidates any stored session data.
        
        Returns:
            True if logout was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def get_pending_payments(self) -> List[Payment]:
        """Retrieve list of pending tax payments.
        
        Fetches all outstanding tax obligations from AFIP for the authenticated
        account. Requires an active session.
        
        Returns:
            List of Payment objects representing pending obligations.
            
        Raises:
            Exception: If not logged in or if there's an error retrieving data.
        """
        pass
    
    @abstractmethod
    async def get_session(self) -> Optional[AFIPSession]:
        """Get the current active session.
        
        Returns information about the current session if one exists.
        
        Returns:
            AFIPSession object if logged in, None otherwise.
        """
        pass
    
    @abstractmethod
    async def restore_session(self, session: AFIPSession) -> bool:
        """Restore a previously saved session.
        
        Attempts to restore a session to avoid re-authentication. This is useful
        for maintaining persistent sessions across application restarts.
        
        Args:
            session: Previously saved session information.
            
        Returns:
            True if the session was successfully restored and is valid,
            False if restoration failed or the session has expired.
        """
        pass
    
    @abstractmethod
    async def get_account_statement(
        self, 
        period_from: Optional[str] = None,
        period_to: Optional[str] = None,
        calculation_date: Optional[str] = None
    ) -> Optional[AccountStatement]:
        """Get account statement with total debt amount.
        
        Retrieves the account statement from AFIP, takes a screenshot,
        and extracts the total debt amount.
        
        Args:
            period_from: Start period in MM/YYYY format (default: 01 of current year).
            period_to: End period in MM/YYYY format (default: current month).
            calculation_date: Calculation date in DD/MM/YYYY format (default: today).
            
        Returns:
            AccountStatement object with debt info and screenshot path,
            or None if retrieval failed.
        """
        pass



class ISessionStorage(ABC):
    """Interface for session persistence.
    
    Defines the contract for storing and retrieving AFIP sessions.
    Implementations can use different storage backends (file system,
    database, memory, etc.) while maintaining the same interface.
    """
    
    @abstractmethod
    async def save(self, session: AFIPSession) -> bool:
        """Save a session to storage.
        
        Persists session information for later retrieval. The implementation
        should handle encryption and secure storage of sensitive data.
        
        Args:
            session: Session information to save.
            
        Returns:
            True if the session was saved successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Load a saved session.
        
        Retrieves a previously saved session for the given CUIT.
        
        Args:
            cuit: Tax ID to look up the session for.
            
        Returns:
            The saved session if found and valid, None otherwise.
        """
        pass
    
    @abstractmethod
    async def delete(self, cuit: str) -> bool:
        """Delete a saved session.
        
        Removes a session from storage. This should be called when a session
        is invalidated or when the user explicitly logs out.
        
        Args:
            cuit: Tax ID associated with the session to delete.
            
        Returns:
            True if the session was deleted successfully, False if not found.
        """
        pass
    
    @abstractmethod
    async def is_valid(self, session: AFIPSession) -> bool:
        """Check if a session is still valid.
        
        Validates a session by checking its expiration time and other
        validity criteria. This method should not make network requests.
        
        Args:
            session: Session to validate.
            
        Returns:
            True if the session appears valid, False otherwise.
        """
        pass