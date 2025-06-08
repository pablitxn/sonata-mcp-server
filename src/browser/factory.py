"""
Browser engine factory
Design Pattern: Factory Method + Registry Pattern
"""
from typing import Type, Dict
import structlog

from .interfaces import IBrowserEngine, BrowserType, BrowserConfig
from .engines.playwright_engine import PlaywrightEngine
from .engines.selenium_engine import SeleniumEngine

logger = structlog.get_logger()


class BrowserEngineFactory:
    """
    Factory for creating browser engines
    Historical note: Factory pattern comes from GoF book (1994)
    """

    # Registry of available engines
    _engines: Dict[BrowserType, Type[IBrowserEngine]] = {
        BrowserType.PLAYWRIGHT: PlaywrightEngine,
        BrowserType.SELENIUM: SeleniumEngine,
    }

    @classmethod
    def register_engine(
            cls,
            browser_type: BrowserType,
            engine_class: Type[IBrowserEngine]
    ) -> None:
        """Register a new engine type"""
        cls._engines[browser_type] = engine_class
        logger.info(f"Registered engine: {browser_type.value}")

    @classmethod
    async def create(
            cls,
            browser_type: BrowserType,
            config: BrowserConfig
    ) -> IBrowserEngine:
        """Create and initialize browser engine"""
        if browser_type not in cls._engines:
            raise ValueError(f"Unknown browser type: {browser_type}")

        engine_class = cls._engines[browser_type]
        engine = engine_class()
        await engine.initialize(config)

        logger.info(f"Created {browser_type.value} engine")
        return engine
