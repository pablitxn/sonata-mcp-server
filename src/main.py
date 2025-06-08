import asyncio
from mcp_server.server import mcp, run


async def main():
    await run()


if __name__ == "__main__":
    asyncio.run(main())
