"""Conversational CLI Gmail Assistant using Pydantic AI and MCP.

Connects to mcp_server.server over stdio transport.
Maintains multi-turn chat history and handles security approval
for sensitive email actions (sending & replying) at the application level.
Logs every MCP tool invocation to console and agent.log in JSON Lines format.
"""

import asyncio
import sys

from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.messages import ModelMessage

from approval import process_tool_approval

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

SYSTEM_PROMPT = """You are an intelligent Gmail Assistant connected to Gmail tools via MCP (Model Context Protocol).

Your primary responsibilities:
1. Help the user manage their Gmail inbox (listing emails, reading specific emails, searching emails, sending new emails, and replying to existing threads).
2. Format email lists and email details cleanly using clear, readable Markdown formatting.
3. For non-email questions (such as general knowledge, coding questions, math, or conversation), answer directly without calling any email tools.
4. Only invoke email tools when the user explicitly or implicitly asks for an email operation.
5. If an email operation returns an error or failure message, explain it to the user clearly and politely.
"""


async def main() -> None:
    """Main CLI chat loop."""
    print("=========================================================")
    print("  📧 Gmail Assistant CLI (Pydantic AI + FastMCP)")
    print("  Connected over stdio to mcp_server.server")
    print("  Type 'exit', 'quit', or 'q' to end the session.")
    print("=========================================================\n")

    # Launch MCP server subprocess via stdio
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=".",
    )

    toolset = MCPToolset(
        transport,
        process_tool_call=process_tool_approval,
    )

    agent = Agent(
        "openai:gpt-4o",
        toolsets=[toolset],
        system_prompt=SYSTEM_PROMPT,
    )

    history: list[ModelMessage] = []

    async with agent:
        while True:
            try:
                user_input = await asyncio.to_thread(input, "\nYou > ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "q"):
                    print("\nClosing session. Goodbye!")
                    break

                # Run turn with message history preserved
                result = await agent.run(user_input, message_history=history)
                history = result.all_messages()

                print(f"\nAssistant > {result.output}")

            except KeyboardInterrupt:
                print("\n\nSession interrupted. Goodbye!")
                break
            except Exception as error:
                print(f"\n⚠️  Error during turn: {error}")
                print("The conversation will continue. Please try your request again.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nSession ended.")
