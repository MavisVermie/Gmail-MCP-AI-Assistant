"""Temporary MCP client test — connects to mcp_server/server.py over stdio.

This file does NOT import gmail_client.py directly.
It spawns the FastMCP server as a subprocess and communicates via MCP protocol.
"""

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    # 1. Define how to launch the MCP server subprocess
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=".",
    )

    # 2. Connect to the server via stdio transport
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 3. Initialize the MCP session
            await session.initialize()

            # 4. List all available tools
            tools_result = await session.list_tools()
            print(f"Available MCP tools ({len(tools_result.tools)}):")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description[:80]}...")
            print()

            # 5. Call list_emails with max_results=3
            print("Calling list_emails(max_results=3) via MCP...")
            call_result = await session.call_tool(
                "list_emails",
                arguments={"max_results": 3},
            )

            # 6. Print structured results
            for item in call_result.content:
                if hasattr(item, "text"):
                    data = json.loads(item.text)
                    print(json.dumps(data, indent=2, ensure_ascii=False))

    print("\nSession closed cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
