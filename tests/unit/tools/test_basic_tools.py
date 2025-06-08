import pytest
from unittest.mock import MagicMock
from mcp.server.fastmcp import FastMCP


class TestBasicTools:
    """Test suite for basic MCP tools."""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock FastMCP instance."""
        # Create a mock that tracks decorated functions
        mock_mcp = MagicMock()
        mock_mcp._tools = {}
        mock_mcp._resources = {}
        
        def mock_tool_decorator():
            def decorator(func):
                mock_mcp._tools[func.__name__] = func
                return func
            return decorator
        
        def mock_resource_decorator(path):
            def decorator(func):
                mock_mcp._resources[path] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool_decorator
        mock_mcp.resource = mock_resource_decorator
        
        return mock_mcp
    
    def test_register_basic_tools(self, mock_mcp):
        """Test registering basic tools."""
        from src.mcp_server.tools.basic_tools import register_basic_tools
        
        register_basic_tools(mock_mcp)
        
        # Check that add tool was registered
        assert 'add' in mock_mcp._tools
        
        # Check that greeting resource was registered
        assert 'greeting://{name}' in mock_mcp._resources
    
    def test_add_tool_functionality(self, mock_mcp):
        """Test add tool functionality."""
        from src.mcp_server.tools.basic_tools import register_basic_tools
        
        register_basic_tools(mock_mcp)
        
        add_func = mock_mcp._tools['add']
        
        # Test integer addition
        result = add_func(a=5, b=3)
        assert result == 8
        
        # Test with negative numbers
        result = add_func(a=-5, b=3)
        assert result == -2
        
        # Test with zero
        result = add_func(a=0, b=0)
        assert result == 0
    
    def test_greeting_resource_functionality(self, mock_mcp):
        """Test greeting resource functionality."""
        from src.mcp_server.tools.basic_tools import register_basic_tools
        
        register_basic_tools(mock_mcp)
        
        get_greeting_func = mock_mcp._resources['greeting://{name}']
        
        # Test greeting resource
        result = get_greeting_func(name="World")
        
        assert isinstance(result, str)
        assert result == "Hello, World!"
    
    def test_greeting_with_different_names(self, mock_mcp):
        """Test greeting resource with different names."""
        from src.mcp_server.tools.basic_tools import register_basic_tools
        
        register_basic_tools(mock_mcp)
        
        get_greeting_func = mock_mcp._resources['greeting://{name}']
        
        # Test with various names
        names = ["Alice", "Bob", "Charlie", "123", "Test Name"]
        
        for name in names:
            result = get_greeting_func(name=name)
            assert result == f"Hello, {name}!"