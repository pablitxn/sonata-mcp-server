"""Simplified AFIP tools for MCP server - placeholder implementation.

This module provides MCP tools for interacting with AFIP services.
Currently returns mock data for demonstration purposes.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP


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
        # Mock implementation - returns success for demonstration
        return {
            "success": True,
            "status": "success",
            "message": "Login successful (mock)",
            "session": {
                "cuit": cuit.replace("-", ""),
                "expires_at": "2025-06-08T23:00:00",
                "is_valid": True
            },
            "timestamp": datetime.now().isoformat(),
            "note": "This is a mock implementation. Real AFIP connector integration pending."
        }
    
    
    @mcp.tool()
    async def afip_logout() -> Dict[str, Any]:
        """Logout from the current AFIP session.
        
        Returns:
            Dictionary with logout status
        """
        return {
            "success": True,
            "message": "Logout successful (mock)",
            "timestamp": datetime.now().isoformat()
        }
    
    
    @mcp.tool()
    async def afip_get_account_statement(
        period_from: Optional[str] = None,
        period_to: Optional[str] = None,
        calculation_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get AFIP account statement with total debt and screenshot.
        
        Args:
            period_from: Start period in MM/YYYY format (default: 01/2025)
            period_to: End period in MM/YYYY format (default: 06/2025)
            calculation_date: Calculation date in DD/MM/YYYY format (default: 08/06/2025)
            
        Returns:
            Dictionary with account statement information including total debt and screenshot path
        """
        return {
            "success": True,
            "total_debt": 15000.50,
            "screenshot_path": "/tmp/mock_screenshot.png",
            "period_from": period_from or "01/2025",
            "period_to": period_to or "06/2025",
            "calculation_date": calculation_date or "08/06/2025",
            "retrieved_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "note": "This is a mock implementation. Real AFIP connector integration pending."
        }
    
    
    @mcp.tool()
    async def afip_get_pending_payments() -> Dict[str, Any]:
        """Get list of pending tax payments from AFIP.
        
        Returns:
            Dictionary with list of pending payments
        """
        return {
            "success": True,
            "payments": [
                {
                    "id": "PAY001",
                    "description": "IVA - Junio 2025 (mock)",
                    "amount": 5000.00,
                    "due_date": "2025-07-15T00:00:00",
                    "status": "pending",
                    "tax_type": "IVA",
                    "period": "06/2025"
                }
            ],
            "count": 1,
            "timestamp": datetime.now().isoformat(),
            "note": "This is a mock implementation. Real AFIP connector integration pending."
        }
    
    
    @mcp.tool()
    async def afip_get_session_status() -> Dict[str, Any]:
        """Get current AFIP session status.
        
        Returns:
            Dictionary with session information
        """
        return {
            "success": True,
            "has_session": False,
            "message": "No active session (mock)",
            "timestamp": datetime.now().isoformat(),
            "note": "This is a mock implementation. Real AFIP connector integration pending."
        }