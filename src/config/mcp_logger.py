"""MCP-compatible logger configuration.

This module configures structlog to output JSON-formatted logs that won't
interfere with the MCP protocol communication.
"""

import sys
import structlog
import logging


def configure_mcp_logging():
    """Configure structlog for MCP server compatibility.
    
    MCP servers communicate via JSON-RPC over stdio. Any non-JSON output
    to stdout will break the protocol. This configuration ensures all logs
    are either:
    1. Sent to stderr (which MCP clients typically ignore)
    2. Or formatted as JSON if they must go to stdout
    """
    
    # Configure Python's standard logging to use stderr
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure structlog to use JSON rendering and output to stderr
    structlog.configure(
        processors=[
            # Don't use stdlib processors with PrintLoggerFactory
            # They expect stdlib logger objects, not PrintLogger
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use JSONRenderer instead of ConsoleRenderer for MCP compatibility
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


# Configure logging when module is imported
configure_mcp_logging()

# Export configured logger
logger = structlog.get_logger()