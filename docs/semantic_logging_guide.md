# Semantic Logging Guide for AFIP MCP Server

## Overview

This document describes the semantic logging implementation added throughout the AFIP MCP Server project. The logging follows a consistent pattern to provide better visibility and debugging capabilities.

## Logging Pattern

All log messages follow the pattern: `<module>.<function_name>: <description>`

Examples:
- `connector.login: starting login process`
- `selenium_page.goto: navigating to URL`
- `encrypted_storage.save: session saved and encrypted`

## Modules with Enhanced Logging

### 1. AFIP Connector (`src/connectors/afip/connector.py`)

Key logging points:
- **Login flow**: Each step of the login process including navigation, form filling, captcha detection
- **Session management**: Session restoration, validation, and storage
- **Account statement retrieval**: Detailed logs for each step including element searches, form filling, and data extraction
- **Payment retrieval**: Navigation and data parsing

Example logs:
```
connector.login: starting login process, cuit=20123456789
connector.login: navigating to login page, url=https://auth.afip.gob.ar/contribuyente_/login.xhtml
connector.login: filling username field, cuit_masked=20...89
connector.login: checking for captcha
connector.login: login successful, redirected to portal
```

### 2. Browser Engines

#### Selenium Engine (`src/browser/engines/selenium_engine.py`)
- Page navigation with URLs and titles
- Element interactions (click, fill, wait)
- JavaScript execution
- Screenshot operations
- Cookie management

#### Playwright Engine (`src/browser/engines/playwright_engine.py`)
- Similar logging to Selenium for consistency
- Context creation and management
- Page operations

### 3. Captcha Solving Chain (`src/captcha/`)

#### Chain Management (`chain.py`)
- Solver selection process
- Circuit breaker status
- Solution attempts and results

#### Individual Solvers (`solvers.py`)
- CapSolver, TwoCaptcha, AntiCaptcha
- Captcha type detection
- API communication simulation
- Solution results

### 4. Session Storage (`src/connectors/afip/session/storage.py`)

#### In-Memory Storage
- Session save/load operations
- Expiration checks

#### Encrypted Storage
- File operations with paths
- Encryption/decryption status
- Session validity checks

### 5. MCP Server Tools (`src/mcp_server/tools/afip_tools.py`)
- Tool invocation tracking
- Parameter validation
- Result summaries
- Error handling

## Security Considerations

1. **CUIT Masking**: CUITs are logged with only first 2 and last 2 digits visible
   - Example: `20123456789` → `20...89`

2. **Password Protection**: Passwords are never logged

3. **Sensitive Data**: 
   - API keys are not logged
   - Session tokens are logged with limited information
   - Cookie values are not logged in detail

## Log Levels

- **INFO**: Major operations and successful results
- **DEBUG**: Detailed operation steps and intermediate values
- **WARNING**: Non-critical issues (expired sessions, missing elements)
- **ERROR**: Exceptions with full context and stack traces

## Benefits

1. **Debugging**: Clear visibility into operation flow
2. **Monitoring**: Track success/failure rates
3. **Performance**: Identify slow operations
4. **Security**: Audit trail for access and operations
5. **Support**: Better error diagnosis

## Usage Examples

### Tracking a Login Flow
```
2024-01-20 10:30:01 INFO connector.login: starting login process
2024-01-20 10:30:01 INFO selenium_engine.create_context: creating new context
2024-01-20 10:30:02 INFO selenium_page.goto: navigating to URL
2024-01-20 10:30:03 INFO connector.login: filling username field
2024-01-20 10:30:04 INFO captcha_handler.handle: attempting to solve captcha
2024-01-20 10:30:08 INFO connector.login: login completed successfully
```

### Diagnosing Failures
```
2024-01-20 10:35:01 ERROR connector.get_account_statement: Estado de cuenta button not found
2024-01-20 10:35:01 ERROR connector.get_account_statement: page_url=https://portalcf.cloud.afip.gob.ar/portal/app/
2024-01-20 10:35:01 ERROR connector.get_account_statement: page_title=Portal Contribuyente
```

## Testing

Use the provided test script to verify logging:
```bash
python test_enhanced_logging.py
```

This will demonstrate the logging patterns across different components.