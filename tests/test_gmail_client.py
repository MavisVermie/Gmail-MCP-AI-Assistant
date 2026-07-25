"""Unit tests for Gmail client helper functions."""

from mcp_server.gmail_client import (
    _normalize_recipients,
    _validate_email,
    get_header,
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
