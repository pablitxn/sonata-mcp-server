# 🏗️ Sonata MCP Server Architecture

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Design Patterns](#design-patterns)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Extension Points](#extension-points)
- [Technology Stack](#technology-stack)

## Overview

Sonata MCP Server is a Model Context Protocol (MCP) server that enables AI agents to interact with government websites through automated browser interactions. The architecture is designed with extensibility, security, and reliability at its core.

### Key Architectural Goals
- **Modularity**: Component-based design with clear interfaces
- **Security**: Multi-layered security approach for sensitive government interactions
- **Extensibility**: Easy addition of new government sites and services
- **Reliability**: Fault-tolerant design with circuit breakers and retry mechanisms
- **Testability**: Interface-based design enabling comprehensive testing

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agent (LLM)                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ MCP Protocol
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Sonata MCP Server                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                     MCP Tool Layer                         │ │
│  │  • Basic Tools  • Search Tools  • Memory Tools           │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Connector Layer                           │ │
│  │  • AFIP Connector  • ANSES Connector  • Mi Argentina     │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                Browser Abstraction Layer                   │ │
│  │  • Browser Factory  • Playwright Engine  • Selenium Engine│ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Support Services                          │ │
│  │  • Captcha Chain  • Session Storage  • Authentication    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependency Graph

```
                    ┌─────────────┐
                    │  main.py    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ MCP Server  │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐     ┌──────▼──────┐   ┌─────▼─────┐
    │  Tools  │     │ Connectors  │   │  Memory   │
    └────┬────┘     └──────┬──────┘   └───────────┘
         │                 │
         └────────┬────────┘
                  │
           ┌──────▼──────┐
           │   Browser   │
           │   Factory   │
           └──────┬──────┘
                  │
        ┌─────────┴─────────┐
        │                   │
  ┌─────▼─────┐      ┌──────▼──────┐
  │Playwright │      │  Selenium   │
  │  Engine   │      │   Engine    │
  └───────────┘      └─────────────┘
```

## Core Components

### 1. MCP Server Layer (`src/mcp_server/`)

The entry point for all AI agent interactions.

**Key Files:**
- `server.py`: FastMCP server implementation
- `tools/`: Tool definitions for MCP protocol

**Responsibilities:**
- Handle MCP protocol communication
- Register and expose tools to AI agents
- Manage request/response lifecycle
- Implement 5-minute timeout for long operations

**Design Decisions:**
- FastMCP chosen for its async support and simplicity
- Tool-based architecture for clear capability boundaries
- Long timeout to accommodate government site latencies

### 2. Browser Abstraction Layer (`src/browser/`)

Provides a unified interface for browser automation across different engines.

**Components:**
- **Interfaces** (`interfaces.py`):
  ```python
  IBrowserEngine: Core browser operations
  IBrowserContext: Isolated browser contexts
  IPage: Page interaction methods
  IElement: DOM element interactions
  ```

- **Engines**:
  - `PlaywrightEngine`: Modern, fast browser automation
  - `SeleniumEngine`: Established, widely-supported automation

- **Factory** (`factory.py`):
  - Registry-based pattern for engine registration
  - Lazy initialization for resource efficiency
  - Configuration-driven engine selection

**Key Features:**
- Async-first design with synchronous adapters
- Anti-detection measures (user agents, viewport settings)
- Cookie management for session persistence
- Screenshot capabilities for debugging

### 3. Connector Layer (`src/connectors/`)

Government site-specific implementations.

**AFIP Connector** (`afip/connector.py`):
- Handles Argentina's tax authority website
- Implements login flow with CUIT/password
- Manages complex form submissions
- Retrieves payment obligations and tax information

**Interface Design**:
```python
class IAFIPConnector(ABC):
    async def login(self, cuit: str, password: str) -> LoginResult
    async def get_obligations(self) -> List[Obligation]
    async def submit_declaration(self, data: Dict) -> SubmissionResult
```

**Extension Pattern**:
- Each connector implements a standard interface
- Site-specific logic encapsulated within connector
- Shared utilities for common patterns (login, navigation)

### 4. Captcha Resolution System (`src/captcha/`)

Sophisticated captcha handling with multiple fallback options.

**Architecture**:
```
CaptchaChain (Chain of Responsibility)
    │
    ├─→ CircuitBreaker(CapSolverAI)
    │
    ├─→ CircuitBreaker(2Captcha)
    │
    └─→ CircuitBreaker(AntiCaptcha)
```

**Components**:
- **CaptchaChain**: Orchestrates solver attempts
- **CircuitBreaker**: Prevents cascading failures
- **Solvers**: Service-specific implementations

**Configuration**:
```python
failure_threshold: 3  # Failures before circuit opens
recovery_timeout: 60  # Seconds before retry
half_open_requests: 1 # Test requests in recovery
```

### 5. Session Management (`src/connectors/afip/session/`)

Secure storage and retrieval of authentication sessions.

**Storage Backends**:
1. **InMemorySessionStorage**:
   - Temporary storage for testing
   - No persistence between runs
   - Fast access, no I/O overhead

2. **EncryptedSessionStorage**:
   - Production-ready persistent storage
   - Fernet symmetric encryption
   - File permissions (0o600) for security
   - Automatic key generation and management

**Session Lifecycle**:
```
Login → Create Session → Encrypt → Store
  ↓
Subsequent Request → Load → Decrypt → Validate → Use
  ↓
Expiration → Clear → Re-authenticate
```

### 6. Authentication System (`src/auth/`)

Currently a placeholder for future authentication mechanisms.

**Planned Features**:
- Certificate-based authentication (AFIP requirements)
- OAuth2 support for modern services
- Multi-factor authentication handling
- Token refresh mechanisms

## Design Patterns

### 1. Abstract Factory Pattern
**Usage**: Browser engine creation
```python
class BrowserEngineFactory:
    @classmethod
    def create(cls, engine_type: str) -> IBrowserEngine:
        return cls._registry[engine_type]()
```

### 2. Chain of Responsibility
**Usage**: Captcha resolution
```python
class CaptchaChain:
    def add_solver(self, solver: ICaptchaSolver):
        self._chain.append(CircuitBreaker(solver))
    
    async def solve(self, captcha: Captcha):
        for solver in self._chain:
            if result := await solver.solve(captcha):
                return result
```

### 3. Strategy Pattern
**Usage**: Interchangeable browser engines and storage backends
- Browser engines implement `IBrowserEngine`
- Storage backends implement `ISessionStorage`
- Captcha solvers implement `ICaptchaSolver`

### 4. Circuit Breaker Pattern
**Usage**: External service failure protection
```python
class CircuitBreaker:
    def __init__(self, solver: ICaptchaSolver):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
```

### 5. Dependency Injection
**Usage**: Interface-based component wiring
- Components depend on interfaces, not implementations
- Facilitates testing with mock implementations
- Enables runtime configuration changes

### 6. Singleton Pattern
**Usage**: Browser factory and configuration management
- Single factory instance manages all browser engines
- Configuration loaded once and shared

## Data Flow

### 1. Authentication Flow
```
User Request → MCP Tool → Connector → Browser → Government Site
                ↓                         ↓
            Session Storage ← Authentication Response
```

### 2. Captcha Resolution Flow
```
Page Load → Detect Captcha → Extract Image/Challenge
                ↓
            CaptchaChain → Solver 1 (fail) → Circuit Opens
                ↓
            Solver 2 (success) → Return Solution
                ↓
            Browser → Submit Solution → Continue Flow
```

### 3. Data Retrieval Flow
```
Query Request → Load Session → Navigate to Page
                    ↓
                Parse Data → Transform → Return to Agent
```

## Security Architecture

### 1. Credential Management
- **No hardcoded credentials**: All sensitive data from environment
- **Encrypted storage**: Fernet encryption for session data
- **Secure file permissions**: 0o600 for storage files
- **Key rotation support**: Separate key storage enables rotation

### 2. Browser Security
- **Isolated contexts**: Each session in separate browser context
- **Anti-detection measures**:
  - Realistic user agents
  - Human-like viewport sizes
  - Non-headless mode operation
  - Cookie persistence

### 3. Network Security
- **HTTPS enforcement**: All government communications encrypted
- **Certificate validation**: Proper SSL/TLS verification
- **Rate limiting**: Respectful interaction with government servers

### 4. Audit Trail
- **Structured logging**: Every action logged with context
- **Sensitive data masking**: Credentials never logged in plain text
- **Compliance support**: Detailed audit trail for regulatory requirements

## Extension Points

### 1. Adding New Government Sites

```python
# 1. Create connector interface
class INewSiteConnector(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict) -> bool
    
# 2. Implement connector
class NewSiteConnector(INewSiteConnector):
    def __init__(self, browser_engine: IBrowserEngine):
        self.browser = browser_engine
    
# 3. Register with MCP server
@mcp_server.tool
async def new_site_login(username: str, password: str):
    connector = NewSiteConnector(browser_factory.create())
    return await connector.authenticate({...})
```

### 2. Adding Browser Engines

```python
# 1. Implement IBrowserEngine
class NewBrowserEngine(IBrowserEngine):
    async def new_context(self) -> IBrowserContext:
        # Implementation
    
# 2. Register with factory
BrowserEngineFactory.register("new_engine", NewBrowserEngine)
```

### 3. Adding Captcha Solvers

```python
# 1. Implement ICaptchaSolver
class NewCaptchaSolver(ICaptchaSolver):
    async def solve(self, captcha: Captcha) -> Optional[str]:
        # Implementation
    
# 2. Add to chain
captcha_chain.add_solver(NewCaptchaSolver())
```

### 4. Custom Storage Backends

```python
# 1. Implement ISessionStorage
class RedisSessionStorage(ISessionStorage):
    async def save(self, session_id: str, data: Dict):
        # Redis implementation
    
# 2. Configure connector
connector = AFIPConnector(
    browser=engine,
    session_storage=RedisSessionStorage()
)
```

## Technology Stack

### Core Technologies
- **Python 3.13+**: Modern async/await support
- **FastMCP**: Model Context Protocol server
- **Playwright/Selenium**: Browser automation
- **Pydantic**: Data validation and settings
- **Structlog**: Structured logging
- **Cryptography**: Fernet encryption

### Supporting Libraries
- **httpx**: Modern HTTP client
- **mem0ai**: AI memory integration
- **pytest**: Comprehensive testing
- **webdriver-manager**: Automated driver management

### Development Tools
- **uv**: Fast Python package management
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

## Performance Considerations

### 1. Resource Management
- **Lazy initialization**: Components created only when needed
- **Connection pooling**: Reuse browser instances when possible
- **Async operations**: Non-blocking I/O for scalability

### 2. Caching Strategy
- **Session caching**: Avoid redundant logins
- **Page caching**: Store frequently accessed data
- **Captcha results**: Cache successful solutions

### 3. Optimization Points
- **Parallel operations**: Multiple browser contexts for concurrent requests
- **Selective loading**: Disable images/CSS when not needed
- **Request interception**: Block unnecessary resources

## Monitoring and Observability

### 1. Logging Strategy
- **Structured logs**: JSON format for easy parsing
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Contextual information**: Request IDs, user context, timing

### 2. Metrics Collection
- **Operation timing**: Track performance of each step
- **Success rates**: Monitor reliability
- **Resource usage**: Browser memory and CPU monitoring

### 3. Health Checks
- **Liveness probe**: Basic server availability
- **Readiness probe**: Dependency availability
- **Circuit breaker status**: Monitor external service health

## Future Architectural Considerations

### 1. Scalability
- **Horizontal scaling**: Multiple server instances
- **Queue-based architecture**: Decouple long-running operations
- **Distributed caching**: Share sessions across instances

### 2. Enhanced Security
- **Hardware security modules**: For key management
- **Zero-trust architecture**: Verify every interaction
- **Compliance certifications**: SOC2, ISO 27001

### 3. AI Integration
- **Intelligent form filling**: ML-based field detection
- **Anomaly detection**: Identify unusual patterns
- **Natural language processing**: Better query understanding

### 4. Platform Expansion
- **Mobile app support**: Native mobile automation
- **API gateway**: RESTful API alongside MCP
- **Webhook support**: Event-driven architecture

