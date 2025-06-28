"""
Browser engine factory
Design Pattern: Factory Method + Registry Pattern
"""
from typing import Type, Dict

from config.mcp_logger import logger
from .interfaces import IBrowserEngine, BrowserType, BrowserConfig
from .engines.playwright_engine import PlaywrightEngine
from .engines.selenium_engine import SeleniumEngine


class BrowserEngineFactory:
    """
    Factory for creating browser engines
    Historical note: Factory pattern comes from GoF book (1994)
    """
    
    # Class-level logger
    _logger = logger.bind(component="browser_factory")

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
        cls._logger.info("browser_factory.register_engine: registered new engine",
                        browser_type=browser_type.value,
                        engine_class=engine_class.__name__)

    @classmethod
    async def create(
            cls,
            browser_type: BrowserType,
            config: BrowserConfig
    ) -> IBrowserEngine:
        """Create and initialize browser engine"""
        cls._logger.info("browser_factory.create: creating browser engine",
                        browser_type=browser_type.value,
                        headless=config.headless)
        
        if browser_type not in cls._engines:
            cls._logger.error("browser_factory.create: unknown browser type",
                            browser_type=browser_type.value,
                            available_types=[t.value for t in cls._engines.keys()])
            raise ValueError(f"Unknown browser type: {browser_type}")

        engine_class = cls._engines[browser_type]
        cls._logger.debug("browser_factory.create: instantiating engine",
                         engine_class=engine_class.__name__)
        
        engine = engine_class()
        await engine.initialize(config)

        cls._logger.info("browser_factory.create: engine created successfully",
                        browser_type=browser_type.value,
                        engine_class=engine_class.__name__)
        return engine
