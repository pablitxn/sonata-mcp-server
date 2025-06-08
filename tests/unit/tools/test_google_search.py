import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp.server.fastmcp import FastMCP, Context


class TestGoogleSearchTool:
    """Test suite for Google Search MCP tool."""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock FastMCP instance."""
        # Create a mock that tracks decorated functions
        mock_mcp = MagicMock()
        mock_mcp._tools = {}
        
        def mock_tool_decorator():
            def decorator(func):
                mock_mcp._tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool_decorator
        return mock_mcp
    
    @pytest.fixture
    def mock_webdriver(self):
        """Mock Selenium WebDriver."""
        with patch('src.mcp_server.tools.google_search.webdriver') as mock:
            mock_driver = MagicMock()
            mock_options = MagicMock()
            
            # Setup driver with Spanish date results
            mock_driver.find_element.return_value.text = "Hoy es 6 de enero de 2025"
            mock_driver.find_elements.return_value = [
                MagicMock(text="Lunes, 6 de enero de 2025"),
                MagicMock(text="Resultado de búsqueda 1"),
                MagicMock(text="Resultado de búsqueda 2")
            ]
            mock_driver.quit.return_value = None
            
            # Setup options
            mock.Chrome.return_value = mock_driver
            mock.ChromeOptions.return_value = mock_options
            
            yield {
                'webdriver': mock,
                'driver': mock_driver,
                'options': mock_options
            }
    
    def test_register_google_search_tool(self, mock_mcp):
        """Test registering Google search tool."""
        from src.mcp_server.tools.google_search import register_google_search_tool
        
        register_google_search_tool(mock_mcp)
        
        # Check that search_google_today_wrapper was registered
        assert 'search_google_today_wrapper' in mock_mcp._tools
    
    @pytest.mark.asyncio
    async def test_search_google_today_wrapper(self, mock_mcp, mock_webdriver):
        """Test the wrapper function."""
        from src.mcp_server.tools.google_search import register_google_search_tool
        
        register_google_search_tool(mock_mcp)
        
        wrapper_func = mock_mcp._tools['search_google_today_wrapper']
        
        # Create mock context
        mock_context = MagicMock(spec=Context)
        
        # Call the wrapper
        result = await wrapper_func(mock_context)
        
        # Should return a string with results
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify driver was used
        mock_webdriver['driver'].get.assert_called_once_with("https://www.google.com")
        mock_webdriver['driver'].quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_google_today_no_results(self, mock_mcp, mock_webdriver):
        """Test when no results are found."""
        from src.mcp_server.tools.google_search import register_google_search_tool
        
        # Setup empty results
        mock_webdriver['driver'].find_elements.return_value = []
        mock_webdriver['driver'].find_element.return_value.text = ""
        
        register_google_search_tool(mock_mcp)
        
        wrapper_func = mock_mcp._tools['search_google_today_wrapper']
        
        # Create mock context
        mock_context = MagicMock(spec=Context)
        
        result = await wrapper_func(mock_context)
        
        # Should return error message
        assert "No se encontraron resultados" in result
    
    @pytest.mark.asyncio
    async def test_search_google_today_error_handling(self, mock_mcp, mock_webdriver):
        """Test error handling in search."""
        from src.mcp_server.tools.google_search import register_google_search_tool
        
        # Make driver.get raise an exception
        mock_webdriver['driver'].get.side_effect = Exception("Network error")
        
        register_google_search_tool(mock_mcp)
        
        wrapper_func = mock_mcp._tools['search_google_today_wrapper']
        
        # Create mock context
        mock_context = MagicMock(spec=Context)
        
        result = await wrapper_func(mock_context)
        
        # Should return error message
        assert "Error" in result
        assert "Network error" in result
        
        # Ensure quit is still called
        mock_webdriver['driver'].quit.assert_called_once()
    
    def test_wrapper_function_structure(self, mock_mcp):
        """Test the structure of the wrapper function."""
        from src.mcp_server.tools.google_search import register_google_search_tool
        
        register_google_search_tool(mock_mcp)
        
        wrapper_func = mock_mcp._tools['search_google_today_wrapper']
        
        # Check function name
        assert wrapper_func.__name__ == 'search_google_today_wrapper'
        
        # Check it's an async function
        import inspect
        assert inspect.iscoroutinefunction(wrapper_func)