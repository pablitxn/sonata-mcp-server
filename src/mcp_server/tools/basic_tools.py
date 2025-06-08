from mcp.server.fastmcp import FastMCP


def register_basic_tools(mcp: FastMCP):
    """Register basic mcp_server with the MCP server."""
    
    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b

    @mcp.resource("greeting://{name}")
    def get_greeting(name: str) -> str:
        """Get a personalized greeting"""
        return f"Hello, {name}!"