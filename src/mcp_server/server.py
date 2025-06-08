from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dotenv import load_dotenv
from mem0 import Memory
import os

from utils import get_mem0_client
from mcp_server.tools.basic_tools import register_basic_tools
from mcp_server.tools.google_search import register_google_search_tool
from mcp_server.tools.memory_tools import register_memory_tools

load_dotenv()

DEFAULT_USER_ID = "user"


@dataclass
class Mem0Context:
    """Context for the Mem0 MCP server."""
    mem0_client: Memory


@asynccontextmanager
async def mem0_lifespan(server: FastMCP) -> AsyncIterator[Mem0Context]:
    """
    Manages the Mem0 client lifecycle.

    Args:
        server: The FastMCP server instance

    Yields:
        Mem0Context: The context containing the Mem0 client
    """
    mem0_client = get_mem0_client()

    try:
        yield Mem0Context(mem0_client=mem0_client)
    finally:
        pass


mcp = FastMCP(
    "mcp-mem0",
    description="MCP server for long term memory storage and retrieval with Mem0",
    lifespan=mem0_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8050"))
)


def register_all_tools(mcp_server: FastMCP):
    """Register all tools with the MCP server."""
    register_basic_tools(mcp_server)
    register_google_search_tool(mcp_server)
    register_memory_tools(mcp_server)


register_all_tools(mcp)


async def run():
    transport = os.getenv("TRANSPORT", "sse")
    if transport == 'sse':
        await mcp.run_sse_async()
    else:
        await mcp.run_stdio_async()


__all__ = ['mcp', 'run']