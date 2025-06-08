# Sonata MCP Server Tests

This directory contains the comprehensive test suite for the Sonata MCP Server.

## Test Structure

```
tests/
├── unit/                         # Fast, isolated tests
│   ├── captcha/                 # CAPTCHA handling unit tests
│   │   ├── test_captcha_chain.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_session_storage.py
│   │   └── test_solvers.py
│   ├── connectors/              # Connector unit tests
│   │   └── afip/               # AFIP connector unit tests
│   ├── engines/                 # Browser engine unit tests
│   │   ├── test_browser_interface.py
│   │   ├── test_playwright_engine.py
│   │   └── test_selenium_engine.py
│   ├── factories/               # Factory pattern unit tests
│   │   └── test_factory.py
│   └── mcp_server/              # MCP server unit tests
│       └── tools/              # MCP tools unit tests
│           ├── test_basic_tools.py
│           └── test_google_search.py
│
├── integration/                  # Tests with real browser instances
│   ├── auth/                    # Authentication flow tests
│   ├── captcha/                 # CAPTCHA handling integration tests
│   ├── connectors/              # Browser connector integration tests
│   │   └── afip/               # AFIP connector integration tests
│   │       ├── debug_afip_login.py
│   │       ├── test_afip_connector.py
│   │       ├── test_afip_fields.py
│   │       ├── test_afip_minimal.py
│   │       ├── test_afip_selectors.py
│   │       └── test_afip_submit.py
│   └── engines/                 # Browser engine integration tests
│       ├── test_browser_integration.py
│       └── test_simple_selenium.py
│
├── e2e/                         # End-to-end scenarios
│   ├── scenarios/               # Complete workflow tests
│   └── smoke/                   # Critical path tests
│
├── fixtures/                    # Shared test data & utilities
│   ├── browser_fixtures.py      # Browser-related fixtures
│   ├── mock_responses.py        # Mock HTML responses
│   └── test_pages/              # HTML files for testing
│
├── performance/                 # Load & stress tests
└── conftest.py                 # pytest configuration
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/engines/test_playwright_engine.py
```

### Run with verbose output
```bash
pytest -v
```

## Test Configuration

### pytest.ini Settings

- **Async Support**: `asyncio_mode = auto` - Automatically handles async tests
- **Timeout**: 300 seconds (5 minutes) default timeout per test
- **Coverage**: Minimum 80% coverage requirement (`--cov-fail-under=80`)
- **Logging**: CLI logging enabled at INFO level
- **Warnings**: Treated as errors by default with specific exceptions
- **Markers**: Strict marker enforcement enabled

## Test Markers

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests requiring real browser instances
- `@pytest.mark.e2e` - End-to-end workflow tests
- `@pytest.mark.slow` - Tests that take longer to execute
- `@pytest.mark.asyncio` - Async tests (automatically applied when using async functions)

## Writing Tests

### Unit Tests
Unit tests should be fast and isolated. Mock external dependencies:

```python
@pytest.mark.unit
async def test_navigate(mock_browser_instance):
    mock_browser_instance.navigate.return_value = BrowserResponse(
        url="https://example.com",
        title="Test Page",
        content="<html>...</html>",
        status_code=200
    )
    
    result = await navigate_to_url("https://example.com")
    assert result["url"] == "https://example.com"
```

### Integration Tests
Integration tests use real browser instances:

```python
@pytest.mark.integration
async def test_real_navigation():
    browser = await BrowserFactory.create(config)
    try:
        await browser.launch()
        response = await browser.navigate("https://example.com")
        assert response.status_code == 200
    finally:
        await browser.close()
```

### Using Fixtures
Common fixtures are available in `conftest.py`:

- `event_loop` - Session-scoped event loop for async tests
- `anyio_backend` - Backend configuration for async tests
- `test_browser_config` - Browser configuration for tests
- `mock_browser_instance` - Mocked browser interface
- `mock_browser_factory` - Mock browser factory
- `mock_mcp_server` - Mock MCP server for testing
- `mock_env_vars` - Mock environment variables
- `temp_test_server` - Temporary HTTP server for testing
- `capture_logs` - Capture log output during tests
- `cleanup_browser_instances` - Ensures browser cleanup after tests

## Coverage Requirements

- Minimum coverage: 80%
- Focus on critical paths and edge cases
- Mock external services and APIs
- Test error handling and recovery

## Best Practices

1. **Keep tests fast** - Use mocks for unit tests
2. **Test one thing** - Each test should verify a single behavior
3. **Use descriptive names** - Test names should explain what they test
4. **Clean up resources** - Always close browsers and clean up
5. **Use fixtures** - Reuse common test setup via fixtures
6. **Test edge cases** - Include error conditions and edge cases
7. **Async tests** - Use `async def` for async tests (pytest-asyncio handles them automatically)
8. **Timeouts** - Override default timeout for long-running tests with `@pytest.mark.timeout(seconds)`
9. **Logging** - Tests output logs at INFO level by default for debugging