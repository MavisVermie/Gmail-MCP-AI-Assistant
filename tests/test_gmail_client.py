"""Unit and mock tests for Gmail client operations."""

from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError
import pytest

from mcp_server.reader import get_header, list_emails, read_email
from mcp_server.sender import (
    _normalize_recipients,
    _validate_email,
    reply_to_email,
    send_email,
)


def test_get_header():
    headers = [
        {"name": "From", "value": "alice@example.com"},
        {"name": "Subject", "value": "Hello World"},
    ]
    assert get_header(headers, "From") == "alice@example.com"
    assert get_header(headers, "Subject") == "Hello World"
    assert get_header(headers, "MissingHeader") == "Unknown"
    assert get_header(headers, "MissingHeader", default="") == ""


def test_validate_email():
    assert _validate_email("user@example.com") is True
    assert _validate_email("John Doe <john@example.com>") is True
    assert _validate_email("invalid-email") is False
    assert _validate_email("") is False


def test_normalize_recipients():
    valid, header, invalid = _normalize_recipients("a@example.com, b@example.com")
    assert valid is True
    assert header == "a@example.com, b@example.com"
    assert invalid == []

    valid_bad, header_bad, invalid_bad = _normalize_recipients("a@example.com, bad-email")
    assert valid_bad is False
    assert invalid_bad == ["bad-email"]


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_list_emails_returns_clean_dicts(mock_auth, mock_build):
    """Test that list_emails() returns clean dictionaries with expected fields."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Reset cached service so our mock is used
    import mcp_server.auth
    mcp_server.auth._cached_service = None

    # Mock list() API call
    mock_list_exec = MagicMock()
    mock_list_exec.execute.return_value = {"messages": [{"id": "msg101"}]}
    mock_service.users().messages().list.return_value = mock_list_exec

    # Mock get() API call for message metadata
    mock_get_exec = MagicMock()
    mock_get_exec.execute.return_value = {
        "id": "msg101",
        "snippet": "Test snippet text",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Sat, 25 Jul 2026 12:00:00 GMT"},
            ]
        },
    }
    mock_service.users().messages().get.return_value = mock_get_exec

    results = list_emails(max_results=1)

    assert len(results) == 1
    email = results[0]
    assert email["id"] == "msg101"
    assert email["from"] == "sender@example.com"
    assert email["subject"] == "Test Subject"
    assert email["date"] == "Sat, 25 Jul 2026 12:00:00 GMT"
    assert email["snippet"] == "Test snippet text"


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_read_email_converts_html_to_plain_text(mock_auth, mock_build):
    """Test that read_email() converts HTML body into readable plain text."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Reset cached service so our mock is used
    import mcp_server.auth
    mcp_server.auth._cached_service = None

    # HTML encoded in base64: "<p>Hello <b>World</b></p><script>alert('bad')</script>"
    html_b64 = "PHA+SGVsbG8gPGI+V29ybGQ8L2I+PC9wPjxzY3JpcHQ+YWxlcnQoJ2JhZCcpPC9zY3JpcHQ+"

    mock_get_exec = MagicMock()
    mock_get_exec.execute.return_value = {
        "id": "msg102",
        "threadId": "thread102",
        "payload": {
            "mimeType": "text/html",
            "headers": [
                {"name": "From", "value": "bob@example.com"},
                {"name": "Subject", "value": "HTML Test"},
                {"name": "Date", "value": "Sat, 25 Jul 2026 13:00:00 GMT"},
            ],
            "body": {"data": html_b64},
        },
    }
    mock_service.users().messages().get.return_value = mock_get_exec

    email_data = read_email("msg102")

    assert email_data is not None
    assert email_data["id"] == "msg102"
    assert "Hello" in email_data["body"]
    assert "World" in email_data["body"]
    assert "alert" not in email_data["body"]  # script tag contents stripped


def test_send_email_rejects_invalid_recipient():
    """Test that send_email() rejects invalid recipient email addresses."""
    res = send_email(to="not-a-valid-email", subject="Test", body="Hello")
    assert res["success"] is False
    assert res["id"] is None
    assert "Invalid recipient" in res["message"]


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_gmail_api_error_returns_structured_failure(mock_auth, mock_build):
    """Test that HttpError returns a structured response instead of crashing."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Reset cached service so our mock is used
    import mcp_server.auth
    mcp_server.auth._cached_service = None

    resp = MagicMock(status=404)
    http_err = HttpError(resp, b"Message not found")

    mock_service.users().messages().get.side_effect = http_err
    mock_service.users().messages().send.side_effect = http_err

    # read_email should return None cleanly
    read_res = read_email("nonexistent_id")
    assert read_res is None

    # send_email should return structured error dict cleanly
    send_res = send_email(to="valid@example.com", subject="Hi", body="Text")
    assert send_res["success"] is False
    assert send_res["id"] is None
    assert "Gmail API error" in send_res["message"]


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_reply_to_email_preserves_thread_id(mock_auth, mock_build):
    """Test that reply_to_email() preserves the original threadId."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Reset cached service so our mock is used
    import mcp_server.auth
    mcp_server.auth._cached_service = None

    # Original message fetch mock
    mock_get_exec = MagicMock()
    mock_get_exec.execute.return_value = {
        "id": "orig_msg_1",
        "threadId": "target_thread_999",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Important Question"},
                {"name": "Message-ID", "value": "<orig123@mail.com>"},
            ]
        },
    }
    mock_service.users().messages().get.return_value = mock_get_exec

    # Reply send mock
    mock_send_exec = MagicMock()
    mock_send_exec.execute.return_value = {
        "id": "reply_msg_2",
        "threadId": "target_thread_999",
    }
    mock_service.users().messages().send.return_value = mock_send_exec

    res = reply_to_email("orig_msg_1", "Here is my reply.")

    assert res["success"] is True
    assert res["id"] == "reply_msg_2"
    assert res["thread_id"] == "target_thread_999"

    # Verify that send() received threadId in the payload dictionary
    send_call_args = mock_service.users().messages().send.call_args
    assert send_call_args is not None
    payload_sent = send_call_args.kwargs.get("body", {})
    assert payload_sent.get("threadId") == "target_thread_999"
