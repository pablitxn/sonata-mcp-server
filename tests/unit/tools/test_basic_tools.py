import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp_server.tools.basic_tools import (
    navigate_to_url,
    take_screenshot,
    search_google,
    get_page_content,
    click_element,
    fill_form_field,
    execute_javascript
)
from src.browser.protocols import BrowserResponse, PageScreenshot


@pytest.fixture
def mock_browser_instance():
    """Mock browser instance for testing."""
    mock_instance = AsyncMock()
    mock_instance.navigate.return_value = BrowserResponse(
        url="https://example.com",
        title="Test Page",
        content="<html><body>Test Content</body></html>",
        status_code=200
    )
    mock_instance.screenshot.return_value = PageScreenshot(
        data=b"fake_screenshot_data",
        format="png"
    )
    mock_instance.execute_script.return_value = {"result": "test"}
    return mock_instance


@pytest.fixture
def mock_browser_factory(mock_browser_instance):
    """Mock browser factory."""
    with patch('src.mcp_server.tools.basic_tools.BrowserFactory') as mock_factory:
        mock_factory.get_instance.return_value = mock_browser_instance
        yield mock_factory


class TestBasicTools:
    """Test suite for basic MCP tools."""
    
    async def test_navigate_to_url(self, mock_browser_factory, mock_browser_instance):
        """Test navigating to a URL."""
        result = await navigate_to_url(url="https://example.com")
        
        mock_browser_factory.get_instance.assert_called_once()
        mock_browser_instance.navigate.assert_called_once_with("https://example.com", timeout=30)
        
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert result["status_code"] == 200
        assert "Test Content" in result["content"]
    
    async def test_navigate_to_url_with_timeout(self, mock_browser_factory, mock_browser_instance):
        """Test navigating to a URL with custom timeout."""
        await navigate_to_url(url="https://example.com", timeout=60)
        
        mock_browser_instance.navigate.assert_called_once_with("https://example.com", timeout=60)
    
    async def test_take_screenshot(self, mock_browser_factory, mock_browser_instance):
        """Test taking a screenshot."""
        result = await take_screenshot()
        
        mock_browser_factory.get_instance.assert_called_once()
        mock_browser_instance.screenshot.assert_called_once_with(full_page=False)
        
        assert result["format"] == "png"
        assert result["size"] == len(b"fake_screenshot_data")
        assert "base64_data" in result
    
    async def test_take_screenshot_full_page(self, mock_browser_factory, mock_browser_instance):
        """Test taking a full page screenshot."""
        await take_screenshot(full_page=True)
        
        mock_browser_instance.screenshot.assert_called_once_with(full_page=True)
    
    async def test_search_google(self, mock_browser_factory, mock_browser_instance):
        """Test Google search functionality."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test+query",
            title="test query - Google Search",
            content='<div class="g">Result 1</div><div class="g">Result 2</div>',
            status_code=200
        )
        
        result = await search_google(query="test query")
        
        expected_url = "https://www.google.com/search?q=test+query"
        mock_browser_instance.navigate.assert_called_once_with(expected_url, timeout=30)
        
        assert result["query"] == "test query"
        assert result["url"] == expected_url
        assert "results" in result
    
    async def test_search_google_with_num_results(self, mock_browser_factory, mock_browser_instance):
        """Test Google search with custom number of results."""
        await search_google(query="test", num_results=20)
        
        expected_url = "https://www.google.com/search?q=test&num=20"
        mock_browser_instance.navigate.assert_called_once_with(expected_url, timeout=30)
    
    async def test_get_page_content(self, mock_browser_factory, mock_browser_instance):
        """Test getting page content."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://example.com",
            title="Test Page",
            content="<html><body><p>Test paragraph</p></body></html>",
            status_code=200
        )
        
        result = await get_page_content(url="https://example.com")
        
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert "text_content" in result
        assert "html_content" in result
        assert result["status_code"] == 200
    
    async def test_get_page_content_with_selector(self, mock_browser_factory, mock_browser_instance):
        """Test getting page content with CSS selector."""
        mock_browser_instance.execute_script.return_value = "Selected content"
        
        result = await get_page_content(
            url="https://example.com",
            selector=".main-content"
        )
        
        mock_browser_instance.execute_script.assert_called()
        assert "selected_content" in result
    
    async def test_click_element(self, mock_browser_factory, mock_browser_instance):
        """Test clicking an element."""
        result = await click_element(selector="button#submit")
        
        mock_browser_instance.click.assert_called_once_with("button#submit")
        assert result["success"] is True
        assert result["selector"] == "button#submit"
    
    async def test_click_element_failure(self, mock_browser_factory, mock_browser_instance):
        """Test clicking element failure."""
        mock_browser_instance.click.side_effect = Exception("Element not found")
        
        result = await click_element(selector="button#missing")
        
        assert result["success"] is False
        assert "error" in result
    
    async def test_fill_form_field(self, mock_browser_factory, mock_browser_instance):
        """Test filling a form field."""
        result = await fill_form_field(
            selector="input#username",
            value="testuser"
        )
        
        mock_browser_instance.fill.assert_called_once_with("input#username", "testuser")
        assert result["success"] is True
        assert result["selector"] == "input#username"
        assert result["value"] == "testuser"
    
    async def test_fill_form_field_failure(self, mock_browser_factory, mock_browser_instance):
        """Test filling form field failure."""
        mock_browser_instance.fill.side_effect = Exception("Field not found")
        
        result = await fill_form_field(
            selector="input#missing",
            value="test"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    async def test_execute_javascript(self, mock_browser_factory, mock_browser_instance):
        """Test executing JavaScript."""
        script = "return document.title;"
        result = await execute_javascript(script=script)
        
        mock_browser_instance.execute_script.assert_called_once_with(script)
        assert result["success"] is True
        assert result["result"] == {"result": "test"}
    
    async def test_execute_javascript_error(self, mock_browser_factory, mock_browser_instance):
        """Test JavaScript execution error."""
        mock_browser_instance.execute_script.side_effect = Exception("Script error")
        
        result = await execute_javascript(script="invalid script")
        
        assert result["success"] is False
        assert "error" in result
    
    async def test_navigate_invalid_url(self, mock_browser_factory, mock_browser_instance):
        """Test navigating to invalid URL."""
        mock_browser_instance.navigate.side_effect = Exception("Invalid URL")
        
        with pytest.raises(Exception, match="Invalid URL"):
            await navigate_to_url(url="not-a-url")
    
    async def test_screenshot_base64_encoding(self, mock_browser_factory, mock_browser_instance):
        """Test screenshot base64 encoding."""
        import base64
        
        result = await take_screenshot()
        
        decoded_data = base64.b64decode(result["base64_data"])
        assert decoded_data == b"fake_screenshot_data"