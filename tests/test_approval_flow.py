"""Unit tests for application security confirmation flow in main.py."""

import asyncio
from unittest.mock import AsyncMock, patch

from main import process_tool_approval


def test_send_email_prevented_when_user_rejects():
    """Test that send_email is prevented from executing when user rejects approval."""

    async def run_test():
        mock_call_tool = AsyncMock()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            mock_input.return_value = "n"

            res = await process_tool_approval(
                ctx=None,
                call_tool=mock_call_tool,
                tool_name="send_email",
                tool_args={"to": "user@example.com", "subject": "Test", "body": "Hello"},
            )

        assert res["success"] is False
        assert res["id"] is None
        assert "declined by the user" in res["message"]
        # Ensure underlying send_email tool was NEVER called
        mock_call_tool.assert_not_called()

    asyncio.run(run_test())


def test_send_email_executes_when_user_approves():
    """Test that send_email executes when user explicitly approves with 'y'."""

    async def run_test():
        mock_call_tool = AsyncMock()
        mock_call_tool.return_value = {"success": True, "id": "sent101", "thread_id": "thread101"}

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            mock_input.return_value = "y"

            res = await process_tool_approval(
                ctx=None,
                call_tool=mock_call_tool,
                tool_name="send_email",
                tool_args={"to": "user@example.com", "subject": "Test", "body": "Hello"},
            )

        assert res["success"] is True
        assert res["id"] == "sent101"
        # Ensure underlying tool WAS called once
        mock_call_tool.assert_called_once_with(
            "send_email",
            {"to": "user@example.com", "subject": "Test", "body": "Hello"},
        )

    asyncio.run(run_test())


def test_reply_to_email_prevented_when_user_rejects():
    """Test that reply_to_email is prevented from executing when user rejects approval."""

    async def run_test():
        mock_call_tool = AsyncMock()
        mock_call_tool.return_value = {
            "id": "orig_msg_1",
            "from": "alice@example.com",
            "subject": "Original Subject",
        }

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            mock_input.return_value = "n"

            res = await process_tool_approval(
                ctx=None,
                call_tool=mock_call_tool,
                tool_name="reply_to_email",
                tool_args={"message_id": "orig_msg_1", "body": "Reply body"},
            )

        assert res["success"] is False
        assert res["id"] is None
        assert "declined by the user" in res["message"]
        # Ensure reply_to_email tool execution call was NEVER made
        executed_tool_calls = [
            call.args[0] for call in mock_call_tool.call_args_list if call.args
        ]
        assert "reply_to_email" not in executed_tool_calls

    asyncio.run(run_test())
