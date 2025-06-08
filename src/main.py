"""
MCP Government Connector - Main entry point
Historical note: MCP (Model Context Protocol) enables LLMs to interact
with external tools in a standardized way.
"""
import asyncio
import structlog
from pathlib import Path
from typing import Optional

import asyncio
from pathlib import Path
import structlog

from .browser.factory import BrowserEngineFactory
from .browser.interfaces import BrowserType, BrowserConfig
from .mcp_server.server import MCPServer
from .utils.config import load_app_config


# Configure structured logging (better than traditional logging)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def main():
    """Main with dependency injection"""
    # Load configuration
    app_config = load_app_config()

    # Determine browser type from config or environment
    browser_type = BrowserType(
        app_config.get("browser_engine", "playwright")
    )

    # Create browser config
    browser_config = BrowserConfig(
        headless=app_config.get("headless", True),
        proxy=app_config.get("proxy"),
        user_agent=app_config.get("user_agent"),
        extra_args=app_config.get("browser_args", [])
    )

    # Create browser engine using factory
    browser_engine = await BrowserEngineFactory.create(
        browser_type,
        browser_config
    )

    # Inject into MCP server
    server = MCPServer(browser_engine, app_config)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await browser_engine.cleanup()


def run():
    """Entry point for poetry scripts"""
    asyncio.run(main())


if __name__ == "__main__":
    run()