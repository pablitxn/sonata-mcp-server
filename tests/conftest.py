"""
Pytest configuration and shared fixtures for the test suite.
"""
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Dict, Any
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import fixtures from our fixtures module - they will be available when tests run


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """Backend for anyio async tests."""
    return "asyncio"


@pytest.fixture
async def mock_browser_factory():
    """Mock browser factory for testing."""
    from unittest.mock import AsyncMock
    from src.browser.factory import BrowserEngineFactory
    
    mock_instance = AsyncMock()
    
    # Create a new factory instance for testing
    yield mock_instance


@pytest.fixture
def test_browser_config():
    """Test browser configuration."""
    from src.browser.interfaces import BrowserConfig
    
    return BrowserConfig(
        headless=True,
        proxy=None,
        user_agent="Mozilla/5.0 (Test Browser)",
        viewport={"width": 1920, "height": 1080},
        extra_args=["--no-sandbox", "--disable-setuid-sandbox"]
    )


@pytest_asyncio.fixture
async def temp_test_server(tmp_path):
    """Create a temporary test server for integration tests."""
    import aiohttp
    from aiohttp import web
    
    # Create test HTML files
    test_files = {
        "index.html": "<html><body><h1>Test Server</h1></body></html>",
        "form.html": """
        <html><body>
            <form id="test-form">
                <input type="text" name="username" id="username">
                <input type="password" name="password" id="password">
                <button type="submit">Submit</button>
            </form>
        </body></html>
        """,
        "ajax.html": """
        <html><body>
            <div id="content">Initial</div>
            <script>
                setTimeout(() => {
                    document.getElementById('content').innerHTML = 'Updated';
                }, 100);
            </script>
        </body></html>
        """
    }
    
    # Write files to temp directory
    for filename, content in test_files.items():
        (tmp_path / filename).write_text(content)
    
    # Create simple web server
    app = web.Application()
    
    async def serve_file(request):
        filename = request.match_info.get('filename', 'index.html')
        filepath = tmp_path / filename
        if filepath.exists():
            return web.Response(text=filepath.read_text(), content_type='text/html')
        return web.Response(status=404)
    
    app.router.add_get('/', serve_file)
    app.router.add_get('/{filename}', serve_file)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 0)
    await site.start()
    
    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://localhost:{port}"
    
    yield base_url
    
    await runner.cleanup()


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing tools."""
    from unittest.mock import MagicMock
    from mcp.server.fastmcp import FastMCP
    
    server = MagicMock(spec=FastMCP)
    return server


@pytest.fixture
def capture_logs():
    """Capture logs during tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    yield log_capture
    
    # Clean up
    root_logger.removeHandler(handler)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "BROWSER_TYPE": "chromium",
        "HEADLESS": "true",
        "TIMEOUT": "30",
        "LOG_LEVEL": "INFO"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
async def cleanup_browser_instances():
    """Cleanup any browser instances after tests."""
    yield
    
    # Cleanup Playwright browsers
    try:
        pass  # Cleanup happens automatically in tests
    except:
        pass


# Test markers
pytest.mark.slow = pytest.mark.slow
pytest.mark.integration = pytest.mark.integration
pytest.mark.unit = pytest.mark.unit
pytest.mark.e2e = pytest.mark.e2e


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )