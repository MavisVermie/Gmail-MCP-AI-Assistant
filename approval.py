"""Application-level security interceptor for MCP tool calls.

Requires explicit user confirmation before executing send_email
or reply_to_email. Logs every tool invocation via tool_logger.
"""

import asyncio
import time

from tool_logger import log_tool_invocation


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
