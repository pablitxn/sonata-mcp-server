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
        if _browser_factory is None:
            _browser_factory = BrowserEngineFactory()
        
        session_storage = EncryptedSessionStorage("/tmp/afip_sessions")
        browser_config = BrowserConfig(
            headless=os.getenv("AFIP_HEADLESS", "true").lower() == "true",
            viewport={"width": 1280, "height": 720}
        )
        
        _connector_instance = AFIPConnector(
            browser_factory=_browser_factory,
            session_storage=session_storage,
            browser_config=browser_config
        )
    
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
            connector = await _get_connector()
            
            credentials = AFIPCredentials(
                cuit=cuit.replace("-", ""),
                password=password
            )
            
            logger.info("afip_login_attempt", cuit=cuit)
            status = await connector.login(credentials)
            
            result = {
                "success": status == LoginStatus.SUCCESS,
                "status": status.value,
                "message": _get_status_message(status),
                "timestamp": datetime.now().isoformat()
            }
            
            if status == LoginStatus.SUCCESS:
                session = await connector.get_session()
                if session:
                    result["session"] = {
                        "cuit": session.cuit,
                        "expires_at": session.expires_at.isoformat(),
                        "is_valid": session.is_valid
                    }
            
            logger.info("afip_login_result", status=status.value, success=result["success"])
            return result
            
        except Exception as e:
            logger.error("afip_login_error", error=str(e), exc_info=True)
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
            connector = await _get_connector()
            
            success = await connector.logout()
            
            return {
                "success": success,
                "message": "Logout successful" if success else "Logout failed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("afip_logout_error", error=str(e), exc_info=True)
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
            connector = await _get_connector()
            
            session = await connector.get_session()
            if not session:
                return {
                    "success": False,
                    "message": "No active session. Please login first.",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Convert empty strings to None for the connector
            period_from_value = period_from if period_from else None
            period_to_value = period_to if period_to else None
            calculation_date_value = calculation_date if calculation_date else None
            
            logger.info("afip_account_statement_request", 
                       period_from=period_from_value, 
                       period_to=period_to_value,
                       calculation_date=calculation_date_value)
            
            statement = await connector.get_account_statement(
                period_from=period_from_value,
                period_to=period_to_value,
                calculation_date=calculation_date_value
            )
            
            if statement:
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
                return {
                    "success": False,
                    "message": "Failed to retrieve account statement",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("afip_account_statement_error", error=str(e), exc_info=True)
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
            connector = await _get_connector()
            
            session = await connector.get_session()
            if not session:
                return {
                    "success": False,
                    "message": "No active session. Please login first.",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info("afip_pending_payments_request")
            
            payments = await connector.get_pending_payments()
            
            payment_list = []
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
            
            return {
                "success": True,
                "payments": payment_list,
                "count": len(payment_list),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("afip_pending_payments_error", error=str(e), exc_info=True)
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
            connector = await _get_connector()
            session = await connector.get_session()
            
            if session:
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
                return {
                    "success": True,
                    "has_session": False,
                    "message": "No active session",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("afip_session_status_error", error=str(e), exc_info=True)
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