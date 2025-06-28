# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build, Test, and Lint Commands

### Installation & Setup
```bash
# Install dependencies
pip install -e .

# Setup browser automation (Arch Linux)
./scripts/setup_browser.sh

# Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials
```

### Running the Server
```bash
# Run the MCP server
python -m sonata.server
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"       # Skip slow tests

# Run with coverage (minimum 80% required)
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/engines/test_playwright_engine.py

# Run tests for a specific connector
pytest tests/integration/connectors/afip/
```

### Development Tools
```bash
# Generate boilerplate for a new connector
python scripts/generate_connector.py --site "NewSite" --country "AR"

# Run security audit
python scripts/security_audit.py
```

## Architecture Overview

This project implements a Model Context Protocol (MCP) server that enables AI agents to interact with government websites through browser automation. The architecture follows several key design patterns:

### Core Architecture Patterns
1. **Abstract Factory Pattern**: Browser engine creation (Playwright/Selenium)
2. **Chain of Responsibility**: Captcha resolution with circuit breakers
3. **Strategy Pattern**: Interchangeable browser engines and storage backends
4. **Circuit Breaker Pattern**: Protection against external service failures
5. **Dependency Injection**: Interface-based component wiring

### Key Components
- **MCP Server Layer** (`src/mcp_server/`): FastMCP-based server exposing tools to AI agents
- **Browser Abstraction Layer** (`src/browser/`): Unified interface supporting both Playwright and Selenium with anti-detection measures
- **Connector Layer** (`src/connectors/`): Government site-specific implementations (AFIP, ATC Sports)
- **Captcha Resolution** (`src/captcha/`): Multi-solver chain with circuit breakers and fallback mechanisms
- **Session Management** (`src/connectors/afip/session/`): Encrypted session storage with automatic renewal
- **Telemetry** (`src/telemetry/`): Comprehensive logging and monitoring system

### Security Architecture
- All credentials stored in environment variables
- Fernet encryption for session data
- Isolated browser contexts per session
- Audit logging with sensitive data masking
- Sandboxed execution environment for PandasAI operations

## Development Guidelines

Refer to `./docs/architecture.md` for detailed architectural information.
Refer to `./docs/tests.md` for comprehensive testing procedures.

### Testing Requirements
- **Minimum coverage**: 80% (enforced)
- When creating new features, always write corresponding tests
- For browser-related features, always include integration tests within the `connectors` directory

### Code Standards
- All code and comments must be written in English
- Use type hints for all functions
- Follow async/await patterns for I/O operations
- Implement proper error handling with specific exceptions

### Adding New Connectors
1. Create connector interface in `src/connectors/<site>/`
2. Implement browser automation following existing patterns (see AFIP connector)
3. Add comprehensive integration tests
4. Register with MCP server in `src/mcp_server/server.py`

### Browser Automation Guidelines
- Always use anti-detection measures (user agents, viewport randomization)
- Implement rate limiting to respect government servers
- Handle captchas through the captcha resolution chain
- Persist cookies for session management
- Ensure proper resource cleanup in finally blocks