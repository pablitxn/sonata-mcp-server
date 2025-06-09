# Telemetry Module

This module provides a comprehensive telemetry solution for the Sonata MCP Server, integrating observability features with the existing logging infrastructure.

## Features

- **Abstracted Interfaces**: Clean interfaces for telemetry providers
- **Multiple Providers**: Support for different telemetry backends
  - NoOp provider for testing/development
  - Langfuse provider for LLM observability
- **Seamless Integration**: Works with existing structlog configuration
- **Context Managers**: Easy-to-use decorators and context managers
- **LLM Support**: Specialized tracking for LLM operations

## Configuration

Set telemetry provider via environment variables:

```bash
# Choose provider
export TELEMETRY_PROVIDER=langfuse  # or "noop"

# General configuration
export TELEMETRY_SERVICE_NAME=sonata-mcp-server
export TELEMETRY_ENVIRONMENT=production
export TELEMETRY_DEBUG=false

# Langfuse-specific
export LANGFUSE_PUBLIC_KEY=your-public-key
export LANGFUSE_SECRET_KEY=your-secret-key
export LANGFUSE_HOST=https://cloud.langfuse.com
```

## Usage

### Basic Logging with Telemetry

```python
from config.telemetry_logger import logger, add_telemetry_context

# Log with metrics
logger.info(
    "processing.request: completed",
    **add_telemetry_context(
        metric_name="requests.processed",
        metric_value=1,
        metric_tags={"endpoint": "/api/v1/data"},
        request_id="123",
        duration_ms=145.2
    )
)
```

### Traced Operations

```python
from telemetry import traced_operation, SpanKind

# Using context manager
with traced_operation(
    "database.query",
    kind=SpanKind.CLIENT,
    attributes={"query": "SELECT * FROM users"}
):
    result = db.execute(query)
```

### Function Decorators

```python
from telemetry import trace

@trace("api.endpoint", kind=SpanKind.SERVER)
async def handle_request(request):
    # Function is automatically traced
    return {"status": "ok"}
```

### Timing Operations

```python
from telemetry import timed_operation

with timed_operation(
    "external_api.call",
    tags={"api": "payment", "method": "POST"},
    log_slow_threshold_ms=1000
):
    response = await external_api.call()
```

### LLM Tracking

```python
from telemetry import llm_generation

with llm_generation(
    model="gpt-4",
    operation="chat_completion",
    metadata={"temperature": 0.7, "max_tokens": 1000}
) as ctx:
    # Make LLM call
    response = await llm.complete(prompt)
    
    # Store data for telemetry
    ctx["prompt"] = prompt
    ctx["response"] = response
    ctx["tokens"] = {
        "prompt": 150,
        "completion": 250,
        "total": 400
    }
```

## Integration Examples

### AFIP Connector

```python
from telemetry import trace, timed_operation

class AFIPConnector:
    @trace("afip.login", kind=SpanKind.CLIENT)
    async def login(self, cuit: str, password: str):
        with timed_operation("afip.login.duration"):
            # Login implementation
            pass
```

### Browser Operations

```python
from telemetry import traced_operation

async def scrape_page(url: str):
    with traced_operation(
        "browser.scrape",
        attributes={"url": url, "engine": "playwright"}
    ):
        # Scraping logic
        pass
```

### Captcha Solving

```python
from config.telemetry_logger import logger, add_telemetry_context

logger.info(
    "captcha.solved",
    **add_telemetry_context(
        metric_name="captcha.success_rate",
        metric_value=1,
        metric_tags={"provider": "2captcha"},
        solver="2captcha",
        duration_ms=2500
    )
)
```

## Testing

The module includes comprehensive tests:

```bash
# Run telemetry tests
pytest tests/unit/telemetry/

# Test with telemetry enabled
TELEMETRY_PROVIDER=noop pytest
```

## Adding New Providers

To add a new telemetry provider:

1. Create provider class implementing `ITelemetryProvider`
2. Place in `src/telemetry/providers/`
3. Register in factory or use lazy loading
4. Add provider-specific configuration

Example:
```python
from telemetry.interfaces import ITelemetryProvider

class DatadogTelemetryProvider(ITelemetryProvider):
    def initialize(self, config: Dict[str, Any]) -> None:
        # Initialize Datadog client
        pass
    
    # Implement other required methods
```

## Best Practices

1. **Use semantic names**: Follow pattern `module.operation`
2. **Add context**: Include relevant attributes for debugging
3. **Mask sensitive data**: Never log passwords, full CUITs, etc.
4. **Use appropriate span kinds**: SERVER, CLIENT, INTERNAL
5. **Track errors**: Use `record_exception=True` for error tracking
6. **Set thresholds**: Use `log_slow_threshold_ms` for performance monitoring

## Performance Impact

The telemetry system is designed for minimal overhead:
- NoOp provider has zero overhead when disabled
- Async operations for non-blocking telemetry
- Efficient batching of telemetry data
- Configurable sampling rates