#!/usr/bin/env python3
"""Quick test script for AFIP MCP tools."""

import asyncio
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from src.mcp_server.tools.afip_tools import register_afip_tools


@pytest.mark.skip(reason="Debug script - not a real test")
async def test_afip_tools():
    """Test AFIP tools registration and basic functionality."""
    # Create MCP server
    mcp = FastMCP("test-afip-server")
    
    # Register AFIP tools
    register_afip_tools(mcp)
    
    print("AFIP Tools registered successfully!")
    print("\nAvailable tools:")
    
    # List registered tools
    for tool_name in dir(mcp):
        if not tool_name.startswith('_'):
            attr = getattr(mcp, tool_name)
            if callable(attr) and hasattr(attr, '__name__'):
                if attr.__name__ in ['afip_login', 'afip_logout', 'afip_get_account_statement', 
                                     'afip_get_pending_payments', 'afip_get_session_status']:
                    print(f"  - {attr.__name__}")
    
    print("\nTools are ready to be used via MCP protocol!")
    print("\nExample usage via MCP client:")
    print('  await client.call_tool("afip_login", {"cuit": "20-12345678-9", "password": "mypassword"})')
    print('  await client.call_tool("afip_get_account_statement", {"period_from": "01/2025"})')
    print('  await client.call_tool("afip_get_session_status", {})')


if __name__ == "__main__":
    asyncio.run(test_afip_tools())