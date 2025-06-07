# 🎼 Sonata MCP Server

> *"Like a musical sonata with multiple movements, each government connector plays its part in the symphony of digital bureaucracy automation"*

A Model Context Protocol (MCP) server that provides LLM agents with the ability to interact with government websites through a unified interface. Sonata orchestrates browser automation to handle authentication, navigation, and form submission across multiple governmental platforms.

## 🎯 What is Sonata?

Sonata MCP Server bridges the gap between AI agents and government digital services by:
- **Automating Authentication**: Secure login handling with MFA support
- **Structured Interactions**: Converting web interfaces into programmable APIs  
- **Session Management**: Maintaining persistent authenticated sessions
- **Security First**: Encrypted credential storage and sandboxed browser contexts

### Why "Sonata"?
In classical music, a sonata consists of multiple movements working together to create a complete piece. Similarly, our server coordinates multiple connectors (movements) to create a harmonious interaction with government services.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/pablitxn/sonata-mcp-server
cd sonata-mcp-server

# Install dependencies
pip install -e .

# Setup browser automation (Arch Linux)
./scripts/setup_browser.sh

# Configure your first connector
cp .env.example .env
# Edit .env with your settings

# Run the MCP server
python -m sonata.server
```

## 📋 Features

- **Multi-Site Support**: Extensible architecture for adding new government sites
- **Async Operations**: Built on modern Python async/await patterns
- **Browser Automation**: Playwright-based automation with anti-detection measures
- **Secure Credential Management**: System keyring integration with encryption
- **Rate Limiting**: Respectful interaction with government servers
- **Comprehensive Logging**: Detailed audit trails for compliance

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  LLM Agent  │────▶│ MCP Protocol│────▶│   Sonata    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼──────┐          ┌────────▼────────┐
              │   AFIP    │            │    ANSES     │          │  Mi Argentina   │
              │ Connector │            │  Connector   │          │   Connector     │
              └───────────┘            └──────────────┘          └─────────────────┘
```

## 🔧 Supported Sites

| Site | Country | Status | Features |
|------|---------|--------|----------|
| AFIP | 🇦🇷 Argentina | ✅ Active | Tax returns, invoicing |
| ANSES | 🇦🇷 Argentina | 🚧 In Progress | Social security queries |
| Mi Argentina | 🇦🇷 Argentina | 📋 Planned | Digital ID, certificates |

## 📖 Usage Example

```python
# Example: Query tax status through LLM
prompt = """
Check my tax status on AFIP and summarize any pending obligations
"""

# The LLM can now use Sonata MCP tools:
# - sonata.authenticate(site="afip", credentials=vault_ref)
# - sonata.navigate(path="/tax-status")
# - sonata.extract_data(selector=".obligations")
```

## 🔒 Security Considerations

Sonata implements multiple security layers:

1. **Credential Isolation**: Each site has isolated credential storage
2. **Browser Sandboxing**: Separate browser contexts per session
3. **Audit Logging**: All actions are logged for compliance
4. **Rate Limiting**: Prevents overwhelming government servers
5. **Encryption at Rest**: All sensitive data encrypted using Fernet

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires test credentials)
pytest tests/integration/

# Run security audit
python scripts/security_audit.py
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Adding a New Connector

```bash
# Generate boilerplate for a new connector
python scripts/generate_connector.py --site "NewSite" --country "AR"
```

## 📚 Historical Context

The concept of programmatic access to government services has evolved significantly:

- **1990s**: Early e-government initiatives, mostly static HTML
- **2000s**: Web services (SOAP) for B2B interactions
- **2010s**: RESTful APIs and open data movements
- **2020s**: AI-driven automation and MCP protocols

Sonata represents the next evolution: making legacy web interfaces accessible to AI agents while respecting security and rate limits.

## ⚠️ Disclaimer

This tool is designed for legitimate automation of personal interactions with government services. Users are responsible for complying with each site's terms of service and applicable laws.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

<p align="center">
  <i>"Turning bureaucracy into symphony, one automation at a time"</i>
</p>

<p align="center">
  Built with ❤️ for the open government data community
</p>

---
