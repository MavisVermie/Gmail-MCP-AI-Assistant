"""Gmail label management and thread operations.

Provides label listing/modification and full thread view
for the MCP agent.
"""

import logging

from googleapiclient.errors import HttpError

from mcp_server.auth import get_service
from mcp_server.reader import _extract_body_and_attachments, get_header


logger = logging.getLogger(__name__)


def list_labels() -> list[dict]:
    """Return all Gmail labels for the authenticated account."""

    try:
        service = get_service()
        response = service.users().labels().list(userId="me").execute()
        labels = response.get("labels", [])

        return [
            {
                "id": label.get("id", ""),
                "name": label.get("name", ""),
                "type": label.get("type", ""),
            }
            for label in labels
        ]

    except HttpError as error:
        logger.error("Gmail API error listing labels: %s", error)
        return []
    except Exception as error:
        logger.error("Unexpected error listing labels: %s", error)
        return []


def modify_labels(
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
) -> dict:
    """Add or remove labels from a Gmail message.

    Common label IDs: INBOX, UNREAD, STARRED, SPAM, TRASH, IMPORTANT.
    """

    if not message_id or not message_id.strip():
        return {
            "success": False,
            "message": "Message ID cannot be empty.",
        }

    add_labels = add_labels or []
    remove_labels = remove_labels or []

    if not add_labels and not remove_labels:
        return {
            "success": False,
            "message": "At least one label to add or remove is required.",
        }

    try:
        service = get_service()
        service.users().messages().modify(
            userId="me",
            id=message_id.strip(),
            body={
                "addLabelIds": add_labels,
                "removeLabelIds": remove_labels,
            },
        ).execute()

        return {
            "success": True,
            "message": f"Labels updated for message {message_id}.",
        }

    except HttpError as error:
        if error.resp.status == 404:
            return {
                "success": False,
                "message": f"Message not found: {message_id}",
            }
        return {
            "success": False,
            "message": f"Gmail API error modifying labels: {error}",
        }
    except Exception as error:
        return {
            "success": False,
            "message": f"Unexpected error modifying labels: {error}",
        }


def get_thread(thread_id: str) -> dict | None:
    """Fetch all messages in a Gmail thread and return them as a conversation.

    Returns a dictionary with thread metadata and a list of messages,
    each containing the same fields as read_email().
    """

    if not thread_id or not thread_id.strip():
        return None

    try:
        service = get_service()
        thread_data = (
            service.users()
            .threads()
            .get(
                userId="me",
                id=thread_id.strip(),
                format="full",
            )
            .execute()
        )
    except HttpError as error:
        if error.resp.status == 404:
            logger.warning("Thread not found: %s", thread_id)
            return None
        logger.error("Gmail API error fetching thread %s: %s", thread_id, error)
        return None
    except Exception as error:
        logger.error("Error fetching thread %s: %s", thread_id, error)
        return None

    raw_messages = thread_data.get("messages", [])
    messages = []

    for msg in raw_messages:
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body, attachments = _extract_body_and_attachments(payload)

        messages.append(
            {
                "id": msg.get("id", ""),
                "thread_id": msg.get("threadId", thread_id),
                "from": get_header(headers, "From"),
                "to": get_header(headers, "To", default=""),
                "cc": get_header(headers, "Cc", default=""),
                "subject": get_header(headers, "Subject"),
                "date": get_header(headers, "Date"),
                "body": body,
                "attachments": attachments,
            }
        )

    return {
        "thread_id": thread_data.get("id", thread_id),
        "message_count": len(messages),
        "messages": messages,
    }
