"""AFIP Connector Package.

This package implements the connector for interacting with AFIP web services.
AFIP (Administración Federal de Ingresos Públicos) is Argentina's federal tax agency.

The connector provides automated access to AFIP's online services including:
- Secure login with captcha handling
- Session management and persistence
- Payment information retrieval
- Logout functionality
"""

# Main connector implementation
from .connector import AFIPConnector

# Interface definition for type safety and testing
from .interfaces import IAFIPConnector

# Public API exports
__all__ = ["AFIPConnector", "IAFIPConnector"]