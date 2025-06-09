from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .tools.basic_tools import register_basic_tools
from .tools.google_search import register_google_search_tool
from .tools.afip_tools import register_afip_tools
from .tools.atc_sports_tools import ATC_SPORTS_TOOLS, execute_atc_sports_tool
# from mcp_server.mcp_server.memory_tools import register_memory_tools

load_dotenv()

DEFAULT_USER_ID = "user"


mcp = FastMCP(
    "mcp-mem0",
    description="MCP server for long term memory storage and retrieval with Mem0",
    request_timeout=300  # 5 minutes timeout for long-running operations
)


def register_atc_sports_tools(mcp_server: FastMCP):
    """Register ATC Sports tools with the MCP server."""
    # Create a closure for each tool to capture the tool name
    def create_tool_handler(name: str):
        async def handler(**kwargs):
            return await execute_atc_sports_tool(name, kwargs)
        return handler
    
    for tool in ATC_SPORTS_TOOLS:
        # Register each tool with its handler
        mcp_server.tool(tool.name)(create_tool_handler(tool.name))


def register_all_tools(mcp_server: FastMCP):
    """Register all mcp_server with the MCP server."""
    register_basic_tools(mcp_server)
    register_google_search_tool(mcp_server)
    register_afip_tools(mcp_server)
    register_atc_sports_tools(mcp_server)
    # register_memory_tools(mcp_server)


register_all_tools(mcp)


__all__ = ['mcp']