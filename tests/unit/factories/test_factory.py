import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserType, BrowserConfig, IBrowserEngine


class TestBrowserEngineFactory:
    """Test suite for BrowserEngineFactory."""
    
    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """Clear the engine registry before each test."""
        BrowserEngineFactory._engines.clear()
        yield
        BrowserEngineFactory._engines.clear()
    
    def test_register_engine(self):
        """Test registering a browser engine."""
        mock_engine_class = MagicMock(spec=IBrowserEngine)
        
        BrowserEngineFactory.register_engine(BrowserType.PLAYWRIGHT, mock_engine_class)
        
        assert BrowserType.PLAYWRIGHT in BrowserEngineFactory._engines
        assert BrowserEngineFactory._engines[BrowserType.PLAYWRIGHT] == mock_engine_class
    
    def test_register_duplicate_engine(self):
        """Test registering duplicate engine overwrites."""
        mock_engine1 = MagicMock(spec=IBrowserEngine)
        mock_engine2 = MagicMock(spec=IBrowserEngine)
        
        BrowserEngineFactory.register_engine(BrowserType.SELENIUM, mock_engine1)
        BrowserEngineFactory.register_engine(BrowserType.SELENIUM, mock_engine2)
        
        assert BrowserEngineFactory._engines[BrowserType.SELENIUM] == mock_engine2
    
    @pytest.mark.asyncio
    async def test_create_registered_engine(self):
        """Test creating an instance of registered engine."""
        # Create a mock engine class
        mock_engine_instance = AsyncMock(spec=IBrowserEngine)
        mock_engine_instance.initialize = AsyncMock()
        
        mock_engine_class = MagicMock(return_value=mock_engine_instance)
        
        BrowserEngineFactory.register_engine(BrowserType.PLAYWRIGHT, mock_engine_class)
        
        config = BrowserConfig(headless=True)
        result = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
        
        # Verify engine was instantiated and initialized
        mock_engine_class.assert_called_once()
        mock_engine_instance.initialize.assert_called_once_with(config)
        assert result == mock_engine_instance
    
    @pytest.mark.asyncio
    async def test_create_unregistered_engine(self):
        """Test creating unregistered engine raises error."""
        config = BrowserConfig(headless=True)
        
        with pytest.raises(ValueError) as exc_info:
            await BrowserEngineFactory.create(BrowserType.PUPPETEER, config)
        
        assert "not registered" in str(exc_info.value)
        assert "PUPPETEER" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_factory_with_real_engines(self):
        """Test factory with real engine imports."""
        # Import real engines to test registration
        from src.browser.engines.playwright_engine import PlaywrightEngine
        from src.browser.engines.selenium_engine import SeleniumEngine
        
        # Register engines
        BrowserEngineFactory.register_engine(BrowserType.PLAYWRIGHT, PlaywrightEngine)
        BrowserEngineFactory.register_engine(BrowserType.SELENIUM, SeleniumEngine)
        
        # Test creation
        config = BrowserConfig(headless=True)
        
        # Mock the initialize method to avoid actual browser launch
        with patch.object(PlaywrightEngine, 'initialize', new_callable=AsyncMock) as mock_pw_init:
            with patch.object(SeleniumEngine, 'initialize', new_callable=AsyncMock) as mock_se_init:
                playwright_engine = await BrowserEngineFactory.create(BrowserType.PLAYWRIGHT, config)
                assert isinstance(playwright_engine, PlaywrightEngine)
                mock_pw_init.assert_called_once_with(config)
                
                selenium_engine = await BrowserEngineFactory.create(BrowserType.SELENIUM, config)
                assert isinstance(selenium_engine, SeleniumEngine)
                mock_se_init.assert_called_once_with(config)
    
    def test_multiple_engine_types(self):
        """Test registering multiple engine types."""
        mock_playwright = MagicMock(spec=IBrowserEngine)
        mock_selenium = MagicMock(spec=IBrowserEngine)
        mock_puppeteer = MagicMock(spec=IBrowserEngine)
        
        BrowserEngineFactory.register_engine(BrowserType.PLAYWRIGHT, mock_playwright)
        BrowserEngineFactory.register_engine(BrowserType.SELENIUM, mock_selenium)
        BrowserEngineFactory.register_engine(BrowserType.PUPPETEER, mock_puppeteer)
        
        assert len(BrowserEngineFactory._engines) == 3
        assert BrowserEngineFactory._engines[BrowserType.PLAYWRIGHT] == mock_playwright
        assert BrowserEngineFactory._engines[BrowserType.SELENIUM] == mock_selenium
        assert BrowserEngineFactory._engines[BrowserType.PUPPETEER] == mock_puppeteer