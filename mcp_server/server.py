"""FastMCP server exposing Gmail client functions as MCP tools.

Run with:  python -m mcp_server.server
Or:        python mcp_server/server.py
"""

from fastmcp import FastMCP

from mcp_server.gmail_client import (
    list_emails as _list_emails,
    read_email as _read_email,
    search_emails as _search_emails,
    send_email as _send_email,
    reply_to_email as _reply_to_email,
)

mcp = FastMCP("Gmail Assistant")


@mcp.tool
def list_emails(
    max_results: int = 5,
    unread_only: bool = False,
    sender: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> list[dict]:
    """List the latest Gmail messages with optional filters.

    Args:
        max_results: Maximum number of emails to return (default 5).
        unread_only: If True, only return unread emails.
        sender: Filter by sender name or email address.
        after: Only return emails after this date (YYYY/MM/DD).
        before: Only return emails before this date (YYYY/MM/DD).

    Returns:
        A list of dictionaries, each containing:
        id, thread_id, from, subject, date, snippet.
    """
    return _list_emails(
        max_results=max_results,
        unread_only=unread_only,
        sender=sender,
        after=after,
        before=before,
    )


@mcp.tool
def read_email(message_id: str) -> dict | None:
    """Read a single Gmail message by its ID and return full details.

    Fetches the complete email including parsed body text and attachment
    metadata. HTML-only emails are converted to readable plain text.

    Args:
        message_id: The Gmail message ID to fetch.

    Returns:
        A dictionary containing: id, thread_id, from, to, cc, subject,
        date, body, and attachments (list of metadata dicts with id,
        filename, mime_type, size). Returns None if the message is not found.
    """
    return _read_email(message_id)


@mcp.tool
def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail using native Gmail search query syntax.

    Supports all standard Gmail search operators such as:
    - from:user@example.com
    - is:unread
    - subject:invoice
    - has:attachment
    - newer_than:7d
    - after:2026/07/01 before:2026/07/25

    Multiple operators can be combined in a single query string.

    Args:
        query: Gmail search query string (e.g. "is:unread from:github.com").
        max_results: Maximum number of results to return (default 10).

    Returns:
        A list of dictionaries, each containing:
        id, thread_id, from, subject, date, snippet.
        Returns an empty list if no matches are found or the query is invalid.
    """
    return _search_emails(query=query, max_results=max_results)


@mcp.tool
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
) -> dict:
    """Compose and send a new email through Gmail.

    Validates recipient addresses and rejects empty subject or body
    before sending.

    Args:
        to: Recipient email address (or comma-separated addresses).
        subject: Email subject line (cannot be empty).
        body: Plain-text email body (cannot be empty).
        cc: Optional CC recipient(s) (comma-separated string).

    Returns:
        A dictionary containing:
        success (bool), id, thread_id, and message.
    """
    return _send_email(to=to, subject=subject, body=body, cc=cc)


@mcp.tool
def reply_to_email(message_id: str, body: str) -> dict:
    """Reply to an existing Gmail message within the same thread.

    Fetches the original email to extract sender, subject, and threading
    headers, then constructs and sends a properly threaded MIME reply.
    The subject is prefixed with 'Re:' only once.

    Args:
        message_id: The Gmail message ID to reply to.
        body: Plain-text reply body (cannot be empty).

    Returns:
        A dictionary containing:
        success (bool), id, thread_id, and message.
    """
    return _reply_to_email(message_id=message_id, body=body)


if __name__ == "__main__":
    mcp.run()
