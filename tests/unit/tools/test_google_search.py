import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp_server.tools.google_search import GoogleSearchTool
from src.browser.protocols import BrowserResponse


@pytest.fixture
def mock_browser_instance():
    """Mock browser instance for testing."""
    mock_instance = AsyncMock()
    return mock_instance


@pytest.fixture
def mock_browser_factory(mock_browser_instance):
    """Mock browser factory."""
    with patch('src.mcp_server.tools.google_search.BrowserFactory') as mock_factory:
        mock_factory.get_instance.return_value = mock_browser_instance
        yield mock_factory


@pytest.fixture
def google_search_tool():
    """Create GoogleSearchTool instance."""
    return GoogleSearchTool()


class TestGoogleSearchTool:
    """Test suite for GoogleSearchTool."""
    
    async def test_search_basic(self, google_search_tool, mock_browser_instance):
        """Test basic Google search."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test+query",
            title="test query - Google Search",
            content='''
            <div class="g">
                <h3>Result 1 Title</h3>
                <a href="https://example1.com">Example 1</a>
                <span>Description for result 1</span>
            </div>
            <div class="g">
                <h3>Result 2 Title</h3>
                <a href="https://example2.com">Example 2</a>
                <span>Description for result 2</span>
            </div>
            ''',
            status_code=200
        )
        
        results = await google_search_tool.search("test query")
        
        assert len(results) == 2
        assert results[0]["title"] == "Result 1 Title"
        assert results[0]["url"] == "https://example1.com"
        assert "Description for result 1" in results[0]["snippet"]
    
    async def test_search_with_num_results(self, google_search_tool, mock_browser_instance):
        """Test search with custom number of results."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test&num=5",
            title="test - Google Search",
            content='<div class="g">Result</div>' * 5,
            status_code=200
        )
        
        results = await google_search_tool.search("test", num_results=5)
        
        expected_url = "https://www.google.com/search?q=test&num=5"
        mock_browser_instance.navigate.assert_called_with(expected_url, timeout=30)
    
    async def test_search_with_lang(self, google_search_tool, mock_browser_instance):
        """Test search with language parameter."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test&hl=es",
            title="test - Google Search",
            content='<div class="g">Resultado</div>',
            status_code=200
        )
        
        await google_search_tool.search("test", lang="es")
        
        expected_url = "https://www.google.com/search?q=test&hl=es"
        mock_browser_instance.navigate.assert_called_with(expected_url, timeout=30)
    
    async def test_parse_search_results(self, google_search_tool):
        """Test parsing search results from HTML."""
        html_content = '''
        <div class="g">
            <h3>Python Programming</h3>
            <a href="https://python.org">Python.org</a>
            <span>Official Python website with documentation</span>
        </div>
        <div class="g">
            <h3>Learn Python</h3>
            <a href="https://learnpython.org">Learn Python</a>
            <span>Interactive Python tutorial</span>
        </div>
        '''
        
        results = google_search_tool._parse_search_results(html_content)
        
        assert len(results) == 2
        assert results[0]["title"] == "Python Programming"
        assert results[0]["url"] == "https://python.org"
        assert "Official Python website" in results[0]["snippet"]
    
    async def test_parse_empty_results(self, google_search_tool):
        """Test parsing when no results found."""
        html_content = '<div>No results found</div>'
        
        results = google_search_tool._parse_search_results(html_content)
        
        assert len(results) == 0
    
    async def test_search_with_site_filter(self, google_search_tool, mock_browser_instance):
        """Test search with site filter."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=python+site%3Agithub.com",
            title="python site:github.com - Google Search",
            content='<div class="g">GitHub result</div>',
            status_code=200
        )
        
        await google_search_tool.search("python site:github.com")
        
        expected_url = "https://www.google.com/search?q=python+site%3Agithub.com"
        mock_browser_instance.navigate.assert_called_with(expected_url, timeout=30)
    
    async def test_search_error_handling(self, google_search_tool, mock_browser_instance):
        """Test error handling during search."""
        mock_browser_instance.navigate.side_effect = Exception("Network error")
        
        with pytest.raises(Exception, match="Network error"):
            await google_search_tool.search("test query")
    
    async def test_extract_clean_url(self, google_search_tool):
        """Test extracting clean URL from Google redirect."""
        google_url = "/url?q=https://example.com/page&sa=U&ved=xyz"
        clean_url = google_search_tool._extract_clean_url(google_url)
        
        assert clean_url == "https://example.com/page"
    
    async def test_extract_clean_url_direct(self, google_search_tool):
        """Test extracting URL when it's already direct."""
        direct_url = "https://example.com/page"
        clean_url = google_search_tool._extract_clean_url(direct_url)
        
        assert clean_url == direct_url
    
    async def test_build_search_url(self, google_search_tool):
        """Test building search URL with parameters."""
        url = google_search_tool._build_search_url(
            query="machine learning",
            num_results=10,
            lang="en"
        )
        
        assert "q=machine+learning" in url
        assert "num=10" in url
        assert "hl=en" in url
        assert url.startswith("https://www.google.com/search?")
    
    async def test_search_with_special_characters(self, google_search_tool, mock_browser_instance):
        """Test search with special characters in query."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test+%26+special+%23chars",
            title="test & special #chars - Google Search",
            content='<div class="g">Result</div>',
            status_code=200
        )
        
        await google_search_tool.search("test & special #chars")
        
        # Check URL encoding
        call_args = mock_browser_instance.navigate.call_args[0][0]
        assert "%26" in call_args or "&" in call_args  # & encoded
        assert "%23" in call_args or "#" in call_args  # # encoded
    
    async def test_search_timeout(self, google_search_tool, mock_browser_instance):
        """Test search with custom timeout."""
        mock_browser_instance.navigate.return_value = BrowserResponse(
            url="https://www.google.com/search?q=test",
            title="test - Google Search",
            content='<div class="g">Result</div>',
            status_code=200
        )
        
        await google_search_tool.search("test", timeout=60)
        
        mock_browser_instance.navigate.assert_called_with(
            "https://www.google.com/search?q=test",
            timeout=60
        )