"""Tests for search_emails — happy path, empty query, pagination, and API errors."""

from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

import mcp_server.auth
from mcp_server.reader import search_emails


def _reset_cache():
    """Reset cached service so mocked build() is used."""
    mcp_server.auth._cached_service = None


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_search_emails_returns_matching_results(mock_auth, mock_build):
    """Happy path — single page of results."""
    _reset_cache()
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_list_exec = MagicMock()
    mock_list_exec.execute.return_value = {
        "messages": [{"id": "s1"}, {"id": "s2"}],
    }
    mock_service.users().messages().list.return_value = mock_list_exec

    mock_get_exec = MagicMock()
    mock_get_exec.execute.return_value = {
        "id": "s1",
        "threadId": "t1",
        "snippet": "matching snippet",
        "payload": {
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "Subject", "value": "Invoice #42"},
                {"name": "Date", "value": "Mon, 01 Aug 2026 09:00:00 GMT"},
            ]
        },
    }
    mock_service.users().messages().get.return_value = mock_get_exec

    results = search_emails("subject:invoice", max_results=5)

    assert len(results) == 2
    assert results[0]["from"] == "alice@example.com"
    assert results[0]["subject"] == "Invoice #42"

    # Verify query was passed through
    call_kwargs = mock_service.users().messages().list.call_args.kwargs
    assert call_kwargs["q"] == "subject:invoice"


def test_search_emails_empty_query_returns_empty_list():
    """Empty or whitespace-only query returns [] without hitting API."""
    assert search_emails("") == []
    assert search_emails("   ") == []


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_search_emails_no_matches_returns_empty_list(mock_auth, mock_build):
    """When the API returns no messages, search returns []."""
    _reset_cache()
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_list_exec = MagicMock()
    mock_list_exec.execute.return_value = {"messages": []}
    mock_service.users().messages().list.return_value = mock_list_exec

    results = search_emails("from:nonexistent@example.com")
    assert results == []


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_search_emails_api_error_returns_empty_list(mock_auth, mock_build):
    """HttpError during search returns [] instead of crashing."""
    _reset_cache()
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    resp = MagicMock(status=500)
    mock_service.users().messages().list.side_effect = HttpError(resp, b"Server error")

    results = search_emails("is:unread")
    assert results == []


@patch("mcp_server.auth.build")
@patch("mcp_server.auth.authenticate_gmail")
def test_search_emails_clamps_max_results(mock_auth, mock_build):
    """max_results is clamped between 1 and 100."""
    _reset_cache()
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_list_exec = MagicMock()
    mock_list_exec.execute.return_value = {"messages": []}
    mock_service.users().messages().list.return_value = mock_list_exec

    # Negative value should be clamped to 1
    search_emails("test", max_results=-5)
    call_kwargs = mock_service.users().messages().list.call_args.kwargs
    assert call_kwargs["maxResults"] == 1

    # Large value should be clamped to 100
    _reset_cache()
    mock_build.return_value = mock_service
    search_emails("test", max_results=999)
    call_kwargs = mock_service.users().messages().list.call_args.kwargs
    assert call_kwargs["maxResults"] == 100
