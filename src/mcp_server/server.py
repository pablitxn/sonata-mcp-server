from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from mcp_server.tools.basic_tools import register_basic_tools
from mcp_server.tools.google_search import register_google_search_tool
# from mcp_server.mcp_server.memory_tools import register_memory_tools

load_dotenv()

DEFAULT_USER_ID = "user"


mcp = FastMCP(
    "mcp-mem0",
    description="MCP server for long term memory storage and retrieval with Mem0",
    request_timeout=300  # 5 minutes timeout for long-running operations
)


def register_all_tools(mcp_server: FastMCP):
    """Register all mcp_server with the MCP server."""
    register_basic_tools(mcp_server)
    register_google_search_tool(mcp_server)
    # register_memory_tools(mcp_server)


register_all_tools(mcp)


__all__ = ['mcp']