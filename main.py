"""Conversational CLI Gmail Assistant using Pydantic AI and MCP.

Connects to mcp_server.server over stdio transport.
Maintains multi-turn chat history and handles security approval
for sensitive email actions (sending & replying) at the application level.
Logs every MCP tool invocation to console and agent.log in JSON Lines format.
"""

import asyncio
import datetime
import json
import logging
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.messages import ModelMessage

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# --- Structured Logging Setup (JSON Lines) ---
logger = logging.getLogger("mcp_agent_logger")
logger.setLevel(logging.INFO)
logger.propagate = False

class JSONLinesFormatter(logging.Formatter):
    """Format log records as raw JSON strings."""
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()

_formatter = JSONLinesFormatter()

_file_handler = logging.FileHandler("agent.log", encoding="utf-8")
_file_handler.setFormatter(_formatter)
logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
logger.addHandler(_console_handler)

SENSITIVE_KEYS = {"token", "credentials", "api_key", "secret", "password", "auth", "key"}


def sanitize_params(params: dict) -> dict:
    """Sanitize parameters before logging.

    Masks sensitive credential/token keys and truncates long email bodies.
    """
    if not isinstance(params, dict):
        return {}

    sanitized = {}
    for key, val in params.items():
        if any(s_key in key.lower() for s_key in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif key == "body" and isinstance(val, str):
            if len(val) > 100:
                sanitized[key] = val[:100] + f"... [truncated, len={len(val)}]"
            else:
                sanitized[key] = val
        else:
            try:
                json.dumps(val)
                sanitized[key] = val
            except TypeError:
                sanitized[key] = str(val)
    return sanitized


def log_tool_invocation(
    tool_name: str,
    params: dict,
    success: bool,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Emit a structured JSON Line log entry to console and agent.log."""
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool_name": tool_name,
        "params": sanitize_params(params),
        "success": success,
        "duration_ms": round(duration_ms, 2),
        "error": error,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


SYSTEM_PROMPT = """You are an intelligent Gmail Assistant connected to Gmail tools via MCP (Model Context Protocol).

Your primary responsibilities:
1. Help the user manage their Gmail inbox (listing emails, reading specific emails, searching emails, sending new emails, and replying to existing threads).
2. Format email lists and email details cleanly using clear, readable Markdown formatting.
3. For non-email questions (such as general knowledge, coding questions, math, or conversation), answer directly without calling any email tools.
4. Only invoke email tools when the user explicitly or implicitly asks for an email operation.
5. If an email operation returns an error or failure message, explain it to the user clearly and politely.
"""


async def process_tool_approval(ctx, call_tool, tool_name: str, tool_args: dict):
    """Application-level security interceptor & structured logger for tool executions.

    Requires explicit user confirmation before executing send_email or reply_to_email.
    Retrieves original message details (recipient & subject) for reply_to_email preview.
    Logs every tool invocation (success, failure, cancellation, exception) in JSON Lines format.
    """
    start_time = time.perf_counter()
    already_logged = False

    try:
        if tool_name == "reply_to_email":
            msg_id = tool_args.get("message_id", "").strip()
            reply_body = tool_args.get("body", "").strip()

            # Retrieve original email metadata for preview using read_email tool
            orig_info = None
            if msg_id:
                try:
                    orig_info = await call_tool("read_email", {"message_id": msg_id})
                except Exception:
                    orig_info = None

            recipient = orig_info.get("from", "Unknown") if isinstance(orig_info, dict) and orig_info else "Unknown"
            orig_subject = orig_info.get("subject", "Unknown") if isinstance(orig_info, dict) and orig_info else "Unknown"

            print("\n" + "=" * 65)
            print("🔒 [SECURITY APPROVAL REQUIRED: REPLY TO EMAIL]")
            print(f"  • Message ID        : {msg_id}")
            print(f"  • Recipient (To)    : {recipient}")
            print(f"  • Original Subject  : {orig_subject}")
            print(f"  • Reply Body        :\n{reply_body}")
            print("=" * 65)

            prompt_str = "Do you approve sending this reply? (y/N): "
            user_response = await asyncio.to_thread(input, prompt_str)
            user_response = user_response.strip().lower()

            if user_response not in ("y", "yes"):
                print("❌ Reply cancelled by user authorization policy.\n")
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_tool_invocation(
                    tool_name=tool_name,
                    params=tool_args,
                    success=False,
                    duration_ms=duration_ms,
                    error="Reply cancelled by user authorization policy.",
                )
                already_logged = True
                return {
                    "success": False,
                    "id": None,
                    "thread_id": None,
                    "message": "Reply action was declined by the user at the application level.",
                }

            print("✅ Reply approved by user. Executing via MCP...\n")

        elif tool_name == "send_email":
            to_addr = tool_args.get("to", "")
            cc_addr = tool_args.get("cc", "")
            subject = tool_args.get("subject", "")
            send_body = tool_args.get("body", "")

            print("\n" + "=" * 65)
            print("🔒 [SECURITY APPROVAL REQUIRED: SEND EMAIL]")
            print(f"  • Recipient (To) : {to_addr}")
            if cc_addr:
                print(f"  • CC             : {cc_addr}")
            print(f"  • Subject        : {subject}")
            print(f"  • Body           :\n{send_body}")
            print("=" * 65)

            prompt_str = "Do you approve sending this email? (y/N): "
            user_response = await asyncio.to_thread(input, prompt_str)
            user_response = user_response.strip().lower()

            if user_response not in ("y", "yes"):
                print("❌ Email dispatch cancelled by user authorization policy.\n")
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_tool_invocation(
                    tool_name=tool_name,
                    params=tool_args,
                    success=False,
                    duration_ms=duration_ms,
                    error="Send email cancelled by user authorization policy.",
                )
                already_logged = True
                return {
                    "success": False,
                    "id": None,
                    "thread_id": None,
                    "message": "Send email action was declined by the user at the application level.",
                }

            print("✅ Email dispatch approved by user. Executing via MCP...\n")

        # Execute tool via MCP
        result = await call_tool(tool_name, tool_args)

        # Inspect tool return for structured errors
        success = True
        error_msg = None

        if isinstance(result, dict):
            if result.get("success") is False:
                success = False
                error_msg = result.get("message", "Tool execution failed.")
            elif result.get("success") is True:
                success = True
                error_msg = None

        duration_ms = (time.perf_counter() - start_time) * 1000
        log_tool_invocation(
            tool_name=tool_name,
            params=tool_args,
            success=success,
            duration_ms=duration_ms,
            error=error_msg,
        )
        already_logged = True

        return result

    except Exception as exc:
        if not already_logged:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_tool_invocation(
                tool_name=tool_name,
                params=tool_args,
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )
        raise exc


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
