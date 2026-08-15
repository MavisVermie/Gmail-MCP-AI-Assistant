"""Gmail write operations — sending emails and replying to threads.

Includes email address validation, recipient normalization,
MIME message construction, and threaded reply logic.
"""

import base64
from email.mime.text import MIMEText
from email.utils import parseaddr
import re

from googleapiclient.errors import HttpError

from mcp_server.auth import get_service
from mcp_server.reader import get_header


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validate_email(email_str: str) -> bool:
    """Validate single email address string."""

    if not email_str or not isinstance(email_str, str):
        return False

    _, addr = parseaddr(email_str)
    target = addr.strip() if addr else email_str.strip()
    return bool(EMAIL_REGEX.match(target))


def _normalize_recipients(recipients: str | list[str] | None) -> tuple[bool, str, list[str]]:
    """Normalize recipients to list of valid email strings.

    Returns (is_valid, formatted_header_str, list_of_invalid_addresses).
    """

    if not recipients:
        return True, "", []

    if isinstance(recipients, str):
        addr_list = [a.strip() for a in recipients.split(",") if a.strip()]
    elif isinstance(recipients, list):
        addr_list = [str(a).strip() for a in recipients if str(a).strip()]
    else:
        return False, "", [str(recipients)]

    invalid_addrs = [addr for addr in addr_list if not _validate_email(addr)]
    formatted_str = ", ".join(addr_list)

    return len(invalid_addrs) == 0, formatted_str, invalid_addrs


def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    cc: str | list[str] | None = None,
) -> dict:
    """Construct a MIME text email and send it via Gmail API."""

    if not subject or not subject.strip():
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": "Email subject cannot be empty.",
        }

    if not body or not body.strip():
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": "Email body cannot be empty.",
        }

    to_valid, to_header, invalid_to = _normalize_recipients(to)
    if not to_valid or not to_header:
        err_msg = f"Invalid recipient email address(es): {', '.join(invalid_to)}" if invalid_to else "Recipient 'to' field is required."
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": err_msg,
        }

    cc_valid, cc_header, invalid_cc = _normalize_recipients(cc)
    if not cc_valid:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Invalid CC email address(es): {', '.join(invalid_cc)}",
        }

    try:
        mime_msg = MIMEText(body, "plain", "utf-8")
        mime_msg["To"] = to_header
        mime_msg["Subject"] = subject
        if cc_header:
            mime_msg["Cc"] = cc_header

        raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
    except Exception as error:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Failed to construct MIME message: {error}",
        }

    try:
        service = get_service()

        sent_msg = (
            service.users()
            .messages()
            .send(
                userId="me",
                body={"raw": raw_bytes},
            )
            .execute()
        )

        return {
            "success": True,
            "id": sent_msg.get("id", ""),
            "thread_id": sent_msg.get("threadId", ""),
            "message": "Email sent successfully.",
        }

    except HttpError as error:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Gmail API error sending email: {error}",
        }
    except Exception as error:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Unexpected error sending email: {error}",
        }


def reply_to_email(message_id: str, body: str) -> dict:
    """Construct and send a MIME reply to an existing email message."""

    if not message_id or not message_id.strip():
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": "Message ID cannot be empty.",
        }

    if not body or not body.strip():
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": "Reply body cannot be empty.",
        }

    try:
        service = get_service()

        # 1. Fetch original message
        try:
            original_data = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id.strip(),
                    format="full",
                )
                .execute()
            )
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "id": None,
                    "thread_id": None,
                    "message": f"Original message not found: {message_id}",
                }
            return {
                "success": False,
                "id": None,
                "thread_id": None,
                "message": f"Gmail API error fetching original message: {error}",
            }

        headers = original_data.get("payload", {}).get("headers", [])
        thread_id = original_data.get("threadId", "")

        # 2. Extract headers (Reply-To / From, Subject, Message-ID, References)
        original_sender = get_header(headers, "Reply-To", default="")
        if not original_sender or original_sender.lower() == "unknown":
            original_sender = get_header(headers, "From", default="")

        if not original_sender or original_sender.lower() == "unknown":
            return {
                "success": False,
                "id": None,
                "thread_id": thread_id or None,
                "message": "Could not determine original sender address.",
            }

        orig_subject = get_header(headers, "Subject", default="")
        if orig_subject.lower() == "unknown":
            orig_subject = ""

        # Format Subject with 'Re:' only once
        if orig_subject.lower().startswith("re:"):
            reply_subject = orig_subject
        elif orig_subject:
            reply_subject = f"Re: {orig_subject}"
        else:
            reply_subject = "Re:"

        orig_msg_id = get_header(headers, "Message-ID", default="")
        if not orig_msg_id or orig_msg_id.lower() == "unknown":
            orig_msg_id = get_header(headers, "Message-Id", default="")
        if orig_msg_id.lower() == "unknown":
            orig_msg_id = ""

        orig_references = get_header(headers, "References", default="")
        if orig_references.lower() == "unknown":
            orig_references = ""

        # 3. Construct MIME reply
        mime_msg = MIMEText(body, "plain", "utf-8")
        mime_msg["To"] = original_sender
        mime_msg["Subject"] = reply_subject

        if orig_msg_id:
            mime_msg["In-Reply-To"] = orig_msg_id
            if orig_references:
                mime_msg["References"] = f"{orig_references} {orig_msg_id}"
            else:
                mime_msg["References"] = orig_msg_id

        raw_bytes = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

        send_payload = {"raw": raw_bytes}
        if thread_id:
            send_payload["threadId"] = thread_id

        # 4. Send reply via Gmail API
        sent_msg = (
            service.users()
            .messages()
            .send(
                userId="me",
                body=send_payload,
            )
            .execute()
        )

        return {
            "success": True,
            "id": sent_msg.get("id", ""),
            "thread_id": sent_msg.get("threadId", thread_id),
            "message": "Reply sent successfully.",
        }

    except HttpError as error:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Gmail API error sending reply: {error}",
        }
    except Exception as error:
        return {
            "success": False,
            "id": None,
            "thread_id": None,
            "message": f"Unexpected error sending reply: {error}",
        }
