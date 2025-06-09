"""MCP-compatible logger with telemetry integration."""

import os
import sys
import structlog
import logging

from src.telemetry.factory import TelemetryFactory
from src.telemetry.processors import TelemetryProcessor, PerformanceProcessor


def configure_telemetry_logging():
    """Configure structlog with telemetry integration for MCP compatibility."""
    
    # Initialize telemetry provider if configured
    telemetry_provider = None
    if os.getenv("TELEMETRY_PROVIDER"):
        try:
            telemetry_provider = TelemetryFactory.create()
        except Exception as e:
            # Log initialization error but continue without telemetry
            logging.error(f"Failed to initialize telemetry: {e}")
    
    # Configure Python's standard logging to use stderr
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Build processor list
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Add performance tracking
        PerformanceProcessor(),
    ]
    
    # Add telemetry processor if provider is available
    if telemetry_provider:
        processors.append(TelemetryProcessor(telemetry_provider))
    
    # JSON renderer for MCP compatibility
    processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


# Configure logging when module is imported
configure_telemetry_logging()

# Export configured logger
logger = structlog.get_logger()

# Export telemetry helpers
from src.telemetry.processors import add_telemetry_context
from src.telemetry.factory import TelemetryFactory


def get_telemetry():
    """Get the current telemetry provider instance."""
    return TelemetryFactory.get_instance()


__all__ = ["logger", "add_telemetry_context", "get_telemetry"]