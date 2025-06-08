"""AFIP Connector Package.

Este paquete implementa el conector para interactuar con los servicios web de AFIP.
"""

from .connector import AFIPConnector
from .interfaces import IAFIPConnector

__all__ = ["AFIPConnector", "IAFIPConnector"]