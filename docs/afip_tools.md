# AFIP MCP Tools Documentation

This document describes the AFIP (Administración Federal de Ingresos Públicos) tools available in the MCP server.

## Overview

The AFIP tools provide automated access to Argentina's federal tax authority web services through the MCP protocol. These tools handle authentication, session management, and data retrieval from AFIP.

## Available Tools

### 1. `afip_login`

Authenticates with AFIP using CUIT and password credentials.

**Parameters:**
- `cuit` (string, required): Tax identification number (11 digits, can include hyphens)
- `password` (string, required): Account password

**Returns:**
```json
{
  "success": true,
  "status": "success",
  "message": "Login successful",
  "session": {
    "cuit": "20123456789",
    "expires_at": "2025-06-08T23:00:00",
    "is_valid": true
  },
  "timestamp": "2025-06-08T21:00:00"
}
```

**Possible status values:**
- `success`: Login completed successfully
- `failed`: Invalid credentials
- `captcha_required`: Captcha could not be solved automatically
- `certificate_required`: Digital certificate authentication required
- `error`: Unexpected error occurred

### 2. `afip_logout`

Logs out from the current AFIP session.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "message": "Logout successful",
  "timestamp": "2025-06-08T21:00:00"
}
```

### 3. `afip_get_account_statement`

Retrieves the account statement ("Estado de cuenta") with total debt amount and takes a screenshot.

**Parameters:**
- `period_from` (string, optional): Start period in MM/YYYY format (default: "01/2025")
- `period_to` (string, optional): End period in MM/YYYY format (default: "06/2025")
- `calculation_date` (string, optional): Calculation date in DD/MM/YYYY format (default: "08/06/2025")

**Returns:**
```json
{
  "success": true,
  "total_debt": 15000.50,
  "screenshot_path": "/tmp/afip_screenshots/estado_cuenta_20123456789_20250608_210000.png",
  "period_from": "01/2025",
  "period_to": "06/2025",
  "calculation_date": "08/06/2025",
  "retrieved_at": "2025-06-08T21:00:00",
  "timestamp": "2025-06-08T21:00:00"
}
```

### 4. `afip_get_pending_payments`

Retrieves the list of pending tax payments.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "payments": [
    {
      "id": "PAY001",
      "description": "IVA - Junio 2025",
      "amount": 5000.00,
      "due_date": "2025-07-15T00:00:00",
      "status": "pending",
      "tax_type": "IVA",
      "period": "06/2025"
    }
  ],
  "count": 1,
  "timestamp": "2025-06-08T21:00:00"
}
```

**Payment status values:**
- `pending`: Payment is due
- `paid`: Payment completed
- `overdue`: Past due date
- `partial`: Partially paid

### 5. `afip_get_session_status`

Checks the current AFIP session status.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "has_session": true,
  "cuit": "20123456789",
  "created_at": "2025-06-08T21:00:00",
  "expires_at": "2025-06-08T23:00:00",
  "is_valid": true,
  "timestamp": "2025-06-08T21:00:00"
}
```

## Usage Examples

### Example 1: Login and Get Account Statement

```python
# Login to AFIP
login_result = await client.call_tool("afip_login", {
    "cuit": "20-12345678-9",
    "password": "mypassword"
})

if login_result["success"]:
    # Get account statement
    statement = await client.call_tool("afip_get_account_statement", {
        "period_from": "01/2025",
        "period_to": "06/2025"
    })
    
    print(f"Total debt: ${statement['total_debt']}")
    print(f"Screenshot saved to: {statement['screenshot_path']}")
```

### Example 2: Check Pending Payments

```python
# Check session status first
status = await client.call_tool("afip_get_session_status", {})

if status["has_session"]:
    # Get pending payments
    payments = await client.call_tool("afip_get_pending_payments", {})
    
    for payment in payments["payments"]:
        print(f"{payment['description']}: ${payment['amount']} - Due: {payment['due_date']}")
else:
    print("No active session. Please login first.")
```

## Configuration

The AFIP tools use the following environment variables:

- `AFIP_HEADLESS`: Set to "true" to run browser in headless mode (default: "false")
- `CAPSOLVER_API_KEY`: API key for CapSolver captcha service
- `TWOCAPTCHA_API_KEY`: API key for 2Captcha service
- `ANTICAPTCHA_API_KEY`: API key for AntiCaptcha service
- `AFIP_DEBUG`: Set to "true" to save debug HTML files

## Security Considerations

1. **Session Storage**: Sessions are encrypted and stored in `/tmp/afip_sessions`
2. **Credentials**: Never log or store plain text passwords
3. **Captcha Solving**: The tools automatically handle captchas using configured services
4. **Browser Security**: Non-headless mode is used by default as AFIP detects headless browsers

## Error Handling

All tools return a consistent error format:

```json
{
  "success": false,
  "message": "Error description",
  "timestamp": "2025-06-08T21:00:00"
}
```

Common errors:
- No active session: Login required
- Session expired: Re-authentication needed
- Network errors: Connection issues with AFIP
- Captcha failures: Unable to solve captcha challenges

## Notes

- AFIP sessions typically expire after 2 hours
- The tools handle session persistence automatically
- Screenshots are saved to `/tmp/afip_screenshots/`
- Browser automation uses Selenium by default for better AFIP compatibility