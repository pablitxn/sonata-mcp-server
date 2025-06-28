"""AFIP tools for MCP server.

This module provides MCP tools for interacting with AFIP services including
authentication and account statement retrieval.

NOTE: This implementation requires fixing the import paths in the AFIP connector
modules to use relative imports instead of absolute 'src.' imports.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Now these imports should work with relative paths
from browser.factory import BrowserEngineFactory
from browser.interfaces import BrowserConfig, BrowserType
from connectors.afip.connector import AFIPConnector
from connectors.afip.interfaces import AFIPCredentials, LoginStatus
from connectors.afip.session.storage import EncryptedSessionStorage
from config.mcp_logger import logger

_connector_instance: Optional[Any] = None
_browser_factory: Optional[Any] = None


async def _get_connector() -> AFIPConnector:
    """Get or create a singleton AFIP connector instance."""
    global _connector_instance, _browser_factory
    
    if _connector_instance is None:
        logger.info("afip_tools._get_connector: Creating new connector instance")
        
        if _browser_factory is None:
            logger.debug("afip_tools._get_connector: Initializing browser factory")
            _browser_factory = BrowserEngineFactory()
        
        session_storage = EncryptedSessionStorage("/tmp/afip_sessions")
        headless_mode = os.getenv("AFIP_HEADLESS", "true").lower() == "true"
        browser_config = BrowserConfig(
            headless=headless_mode,
            viewport={"width": 1280, "height": 720}
        )
        
        logger.debug("afip_tools._get_connector: Browser config created", 
                    headless=headless_mode, 
                    viewport_width=1280, 
                    viewport_height=720)
        
        _connector_instance = AFIPConnector(
            browser_factory=_browser_factory,
            session_storage=session_storage,
            browser_config=browser_config
        )
        
        logger.info("afip_tools._get_connector: Connector instance created successfully")
    
    return _connector_instance


def register_afip_tools(mcp: FastMCP):
    """Register AFIP tools with the MCP server."""
    
    @mcp.tool()
    async def afip_login(cuit: str, password: str) -> Dict[str, Any]:
        """Login to AFIP with CUIT and password.
        
        Args:
            cuit: Tax identification number (11 digits, can include hyphens)
            password: Account password
            
        Returns:
            Dictionary with login status and session information
        """
        try:
            # Mask CUIT for logging (show first 2 and last 2 digits)
            masked_cuit = f"{cuit[:2]}{'*' * (len(cuit.replace('-', '')) - 4)}{cuit.replace('-', '')[-2:]}"
            logger.info("afip_tools.afip_login: Starting login attempt", cuit=masked_cuit)
            
            connector = await _get_connector()
            
            credentials = AFIPCredentials(
                cuit=cuit.replace("-", ""),
                password=password
            )
            
            logger.debug("afip_tools.afip_login: Credentials prepared, calling connector.login")
            status = await connector.login(credentials)
            
            logger.info("afip_tools.afip_login: Login attempt completed", 
                       status=status.value, 
                       status_message=_get_status_message(status))
            
            result = {
                "success": status == LoginStatus.SUCCESS,
                "status": status.value,
                "message": _get_status_message(status),
                "timestamp": datetime.now().isoformat()
            }
            
            if status == LoginStatus.SUCCESS:
                logger.debug("afip_tools.afip_login: Login successful, retrieving session info")
                session = await connector.get_session()
                if session:
                    result["session"] = {
                        "cuit": session.cuit,
                        "expires_at": session.expires_at.isoformat(),
                        "is_valid": session.is_valid
                    }
                    logger.info("afip_tools.afip_login: Session info retrieved", 
                               session_valid=session.is_valid,
                               expires_at=session.expires_at.isoformat())
                else:
                    logger.warning("afip_tools.afip_login: Login successful but no session info available")
            
            return result
            
        except Exception as e:
            logger.error("afip_tools.afip_login: Login failed with exception", 
                        error=str(e), 
                        error_type=type(e).__name__,
                        exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"Error during login: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    
    @mcp.tool()
    async def afip_logout() -> Dict[str, Any]:
        """Logout from the current AFIP session.
        
        Returns:
            Dictionary with logout status
        """
        try:
            logger.info("afip_tools.afip_logout: Starting logout operation")
            
            connector = await _get_connector()
            
            # Check if there's an active session before logout
            session = await connector.get_session()
            if session:
                masked_cuit = f"{session.cuit[:2]}{'*' * (len(session.cuit) - 4)}{session.cuit[-2:]}"
                logger.debug("afip_tools.afip_logout: Active session found", cuit=masked_cuit)
            else:
                logger.warning("afip_tools.afip_logout: No active session to logout from")
            
            success = await connector.logout()
            
            logger.info("afip_tools.afip_logout: Logout operation completed", 
                       success=success,
                       message="Logout successful" if success else "Logout failed")
            
            return {
                "success": success,
                "message": "Logout successful" if success else "Logout failed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("afip_tools.afip_logout: Logout failed with exception", 
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            return {
                "success": False,
                "message": f"Error during logout: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    
    @mcp.tool()
    async def afip_get_account_statement(
        period_from: str = "",
        period_to: str = "",
        calculation_date: str = ""
    ) -> Dict[str, Any]:
        """Get AFIP account statement with total debt and screenshot.
        
        Args:
            period_from: Start period in MM/YYYY format (default: 01/2025)
            period_to: End period in MM/YYYY format (default: 06/2025)
            calculation_date: Calculation date in DD/MM/YYYY format (default: 08/06/2025)
            
        Returns:
            Dictionary with account statement information including total debt and screenshot path
        """
        try:
            logger.info("afip_tools.afip_get_account_statement: Starting account statement retrieval")
            
            connector = await _get_connector()
            
            session = await connector.get_session()
            if not session:
                logger.warning("afip_tools.afip_get_account_statement: No active session found")
                return {
                    "success": False,
                    "message": "No active session. Please login first.",
                    "timestamp": datetime.now().isoformat()
                }
            
            masked_cuit = f"{session.cuit[:2]}{'*' * (len(session.cuit) - 4)}{session.cuit[-2:]}"
            logger.debug("afip_tools.afip_get_account_statement: Session validated", 
                        cuit=masked_cuit,
                        session_valid=session.is_valid)
            
            # Convert empty strings to None for the connector
            period_from_value = period_from if period_from else None
            period_to_value = period_to if period_to else None
            calculation_date_value = calculation_date if calculation_date else None
            
            logger.info("afip_tools.afip_get_account_statement: Requesting statement with parameters", 
                       period_from=period_from_value or "default", 
                       period_to=period_to_value or "default",
                       calculation_date=calculation_date_value or "default")
            
            statement = await connector.get_account_statement(
                period_from=period_from_value,
                period_to=period_to_value,
                calculation_date=calculation_date_value
            )
            
            if statement:
                logger.info("afip_tools.afip_get_account_statement: Statement retrieved successfully",
                           total_debt=statement.total_debt,
                           period_from=statement.period_from,
                           period_to=statement.period_to,
                           calculation_date=statement.calculation_date,
                           screenshot_saved=bool(statement.screenshot_path))
                
                return {
                    "success": True,
                    "total_debt": statement.total_debt,
                    "screenshot_path": statement.screenshot_path,
                    "period_from": statement.period_from,
                    "period_to": statement.period_to,
                    "calculation_date": statement.calculation_date,
                    "retrieved_at": statement.retrieved_at.isoformat(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning("afip_tools.afip_get_account_statement: Failed to retrieve statement")
                return {
                    "success": False,
                    "message": "Failed to retrieve account statement",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("afip_tools.afip_get_account_statement: Statement retrieval failed with exception", 
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            return {
                "success": False,
                "message": f"Error retrieving account statement: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    
    @mcp.tool()
    async def afip_get_pending_payments() -> Dict[str, Any]:
        """Get list of pending tax payments from AFIP.
        
        Returns:
            Dictionary with list of pending payments
        """
        try:
            logger.info("afip_tools.afip_get_pending_payments: Starting pending payments retrieval")
            
            connector = await _get_connector()
            
            session = await connector.get_session()
            if not session:
                logger.warning("afip_tools.afip_get_pending_payments: No active session found")
                return {
                    "success": False,
                    "message": "No active session. Please login first.",
                    "timestamp": datetime.now().isoformat()
                }
            
            masked_cuit = f"{session.cuit[:2]}{'*' * (len(session.cuit) - 4)}{session.cuit[-2:]}"
            logger.debug("afip_tools.afip_get_pending_payments: Session validated", 
                        cuit=masked_cuit,
                        session_valid=session.is_valid)
            
            logger.info("afip_tools.afip_get_pending_payments: Requesting pending payments from connector")
            
            payments = await connector.get_pending_payments()
            
            payment_list = []
            total_amount = 0.0
            
            for payment in payments:
                payment_list.append({
                    "id": payment.id,
                    "description": payment.description,
                    "amount": payment.amount,
                    "due_date": payment.due_date.isoformat(),
                    "status": payment.status.value,
                    "tax_type": payment.tax_type,
                    "period": payment.period
                })
                total_amount += payment.amount
            
            logger.info("afip_tools.afip_get_pending_payments: Payments retrieved successfully",
                       payment_count=len(payment_list),
                       total_amount=total_amount)
            
            return {
                "success": True,
                "payments": payment_list,
                "count": len(payment_list),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("afip_tools.afip_get_pending_payments: Payment retrieval failed with exception", 
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            return {
                "success": False,
                "message": f"Error retrieving payments: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    
    @mcp.tool()
    async def afip_get_session_status() -> Dict[str, Any]:
        """Get current AFIP session status.
        
        Returns:
            Dictionary with session information
        """
        try:
            logger.info("afip_tools.afip_get_session_status: Checking session status")
            
            connector = await _get_connector()
            session = await connector.get_session()
            
            if session:
                masked_cuit = f"{session.cuit[:2]}{'*' * (len(session.cuit) - 4)}{session.cuit[-2:]}"
                logger.info("afip_tools.afip_get_session_status: Active session found",
                           cuit=masked_cuit,
                           is_valid=session.is_valid,
                           created_at=session.created_at.isoformat(),
                           expires_at=session.expires_at.isoformat())
                
                return {
                    "success": True,
                    "has_session": True,
                    "cuit": session.cuit,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "is_valid": session.is_valid,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.info("afip_tools.afip_get_session_status: No active session found")
                return {
                    "success": True,
                    "has_session": False,
                    "message": "No active session",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("afip_tools.afip_get_session_status: Session check failed with exception", 
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True)
            return {
                "success": False,
                "message": f"Error checking session: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


def _get_status_message(status: LoginStatus) -> str:
    """Get human-readable message for login status."""
    messages = {
        LoginStatus.SUCCESS: "Login successful",
        LoginStatus.FAILED: "Login failed - check credentials",
        LoginStatus.CAPTCHA_REQUIRED: "Captcha challenge could not be solved",
        LoginStatus.CERTIFICATE_REQUIRED: "Digital certificate required for this service",
        LoginStatus.SESSION_EXPIRED: "Session has expired"
    }
    return messages.get(status, "Unknown status")