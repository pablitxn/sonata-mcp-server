# PandasAI Telemetry Integration

This document describes the comprehensive telemetry integration for PandasAI within the Sonata MCP Server, providing full visibility into the agent's thinking process, code generation, and execution.

## Overview

The telemetry integration provides:

1. **MCP Protocol Compliance**: All logs are sent via MCP-compliant JSON format to stderr
2. **Langfuse Integration**: LLM calls are tracked with Langfuse for observability
3. **Thinking Process Visibility**: Detailed logs of the agent's reasoning steps
4. **Code Generation Tracking**: Full visibility into prompt generation and code creation
5. **Execution Telemetry**: Tracking of code execution, outputs, and errors

## Architecture

### Components

1. **TelemetryLLM** (`src/agents/pandasai/llm/telemetry_adapter.py`)
   - Wraps LLM calls with telemetry tracking
   - Supports OpenAI, OpenRouter, and Ollama
   - Tracks tokens, latency, and errors
   - Integrates with Langfuse for LLM observability

2. **TelemetryAgent** (`src/agents/pandasai/agent/telemetry_agent.py`)
   - Enhanced PandasAI agent with comprehensive telemetry
   - Tracks query processing phases
   - Monitors retry attempts
   - Provides detailed execution metrics

3. **TelemetryCodeGenerator** (`src/agents/pandasai/core/code_generation/telemetry_generator.py`)
   - Tracks the thinking process during code generation
   - Analyzes prompts and generated code
   - Provides visibility into validation and cleaning steps

4. **TelemetryLogger** (`src/agents/pandasai/helpers/telemetry_logger.py`)
   - Bridges PandasAI's internal logging with MCP telemetry
   - Buffers and analyzes thinking steps
   - Provides structured logging for all operations

## Configuration

### Environment Variables

```bash
# Copy the example configuration
cp .env.telemetry.example .env

# Required: Telemetry provider
TELEMETRY_PROVIDER=langfuse

# Required for Langfuse
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Required for PandasAI
LLM_PROVIDER=openai
LLM_CHOICE=gpt-4o-mini
LLM_API_KEY=your_api_key
```

## Telemetry Events

### 1. Tool Invocation
```json
{
  "event_type": "tool_started",
  "tool_name": "query_spreadsheet",
  "query": "What is the average sales by region?",
  "timestamp": "2024-01-20T10:00:00Z"
}
```

### 2. Thinking Process
```json
{
  "event_type": "thinking_start",
  "phase": "code_generation",
  "steps": [
    {
      "step": "analyzing_dataframes",
      "details": "Understanding available dataframes and their schemas"
    },
    {
      "step": "sql_generation",
      "details": "Generated SQL query for data extraction"
    }
  ]
}
```

### 3. LLM Generation (Langfuse)
- Prompt and completion tracking
- Token usage metrics
- Latency measurements
- Error tracking with stack traces

### 4. Code Execution
```json
{
  "event_type": "execution_completed",
  "duration_ms": 150.5,
  "result_type": "DataFrame",
  "output_preview": "Region | Average Sales\n..."
}
```

## Usage

### Basic Usage

```python
from pandasai.agent.telemetry_agent import TelemetryAgent
from pandasai.llm.telemetry_adapter import TelemetryLLM
from pandasai.dataframe import DataFrame
from pandasai.config import Config

# Initialize LLM with telemetry
llm = TelemetryLLM()

# Create config
config = Config(llm=llm, verbose=True)

# Create agent with telemetry
agent = TelemetryAgent([df], config=config)

# Query will be tracked through all phases
result = agent.chat("What are the top 5 products by revenue?")
```

### MCP Server Integration

The PandasAI tool in the MCP server automatically uses telemetry when configured:

```python
@mcp.tool()
async def query_spreadsheet(file_name: str, query: str) -> TextContent:
    # Telemetry is automatically integrated
    agent = TelemetryAgent([df], config=config)
    result = agent.chat(query)
    return TextContent(type="text", text=str(result))
```

## Viewing Telemetry

### 1. MCP Logs (Real-time)
All telemetry is output to stderr in JSON format, compatible with MCP protocol:

```bash
# View real-time logs
python -m sonata.server 2>&1 | jq '.'
```

### 2. Langfuse Dashboard
Visit your Langfuse instance to view:
- LLM call traces
- Token usage analytics
- Latency distributions
- Error rates

### 3. Structured Log Analysis
Filter specific event types:

```bash
# View only thinking process logs
python -m sonata.server 2>&1 | jq 'select(.event_type == "thinking_step")'

# View only errors
python -m sonata.server 2>&1 | jq 'select(.event_type == "error")'
```

## Benefits

1. **Debugging**: Full visibility into what the agent is doing
2. **Performance Monitoring**: Track latency at each step
3. **Cost Tracking**: Monitor token usage via Langfuse
4. **Error Analysis**: Detailed error tracking with context
5. **Audit Trail**: Complete log of all operations

## Best Practices

1. **Enable telemetry in production** for monitoring and debugging
2. **Use sampling** in high-volume environments (TELEMETRY_SAMPLE_RATE)
3. **Monitor token usage** to control costs
4. **Set up alerts** in Langfuse for errors or high latency
5. **Regularly review thinking logs** to improve prompts

## Troubleshooting

### No telemetry data appearing
1. Check environment variables are set correctly
2. Verify Langfuse credentials are valid
3. Ensure TELEMETRY_PROVIDER is set to "langfuse"

### Missing thinking process logs
1. Verify you're using TelemetryAgent, not the base Agent
2. Check that verbose mode is enabled in Config

### Performance impact
1. Telemetry adds minimal overhead (<5ms per operation)
2. Use sampling if needed: TELEMETRY_SAMPLE_RATE=0.1 (10% of traces)