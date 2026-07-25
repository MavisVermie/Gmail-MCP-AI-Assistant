import base64
from pathlib import Path

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Read-only access for now.
# Later, we will expand this so the app can send and reply.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def authenticate_gmail() -> Credentials:
    """Authenticate the user and return valid Gmail credentials."""

    credentials = None

    # Reuse the saved login token when it exists.
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # Login or refresh the token when necessary.
    if not credentials or not credentials.valid:
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    "credentials.json was not found "
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )

            credentials = flow.run_local_server(port=0)

        # save token
        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials


def get_header(headers: list[dict], header_name: str, default: str = "Unknown") -> str:
    """Find one header, such as Subject or From."""

    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")

    return default


def list_emails(
    max_results: int = 5,
    unread_only: bool = False,
    sender: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> list[dict]:
    """Return basic information about Gmail messages matching optional filters."""

    credentials = authenticate_gmail()

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    query_parts = []
    if unread_only:
        query_parts.append("is:unread")
    if sender:
        query_parts.append(f"from:{sender}")
    if after:
        query_parts.append(f"after:{after}")
    if before:
        query_parts.append(f"before:{before}")

    list_params = {
        "userId": "me",
        "maxResults": max_results,
    }
    if query_parts:
        list_params["q"] = " ".join(query_parts)

    response = service.users().messages().list(**list_params).execute()

    messages = response.get("messages", [])
    results = []

    for message in messages:
        message_data = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )

        headers = message_data.get("payload", {}).get("headers", [])

        results.append(
            {
                "id": message["id"],
                "thread_id": message.get("threadId", ""),
                "from": get_header(headers, "From"),
                "subject": get_header(headers, "Subject"),
                "date": get_header(headers, "Date"),
                "snippet": message_data.get("snippet", ""),
            }
        )

    return results


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail messages using Gmail search query syntax and return clean email metadata."""

    if not query or not query.strip():
        print("Search query cannot be empty.")
        return []

    try:
        credentials = authenticate_gmail()
        service = build("gmail", "v1", credentials=credentials)

        messages = []
        page_token = None

        while len(messages) < max_results:
            fetch_count = min(100, max_results - len(messages))
            params = {
                "userId": "me",
                "q": query.strip(),
                "maxResults": fetch_count,
            }
            if page_token:
                params["pageToken"] = page_token

            response = service.users().messages().list(**params).execute()
            page_messages = response.get("messages", [])
            if not page_messages:
                break

            messages.extend(page_messages)
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        results = []
        for message in messages[:max_results]:
            message_data = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers = message_data.get("payload", {}).get("headers", [])

            results.append(
                {
                    "id": message_data.get("id", message["id"]),
                    "thread_id": message_data.get("threadId", message.get("threadId", "")),
                    "from": get_header(headers, "From"),
                    "subject": get_header(headers, "Subject"),
                    "date": get_header(headers, "Date"),
                    "snippet": message_data.get("snippet", ""),
                }
            )

        return results

    except HttpError as error:
        print(f"Gmail API error during search: {error}")
        return []
    except Exception as error:
        print(f"Unexpected error during search: {error}")
        return []


def _extract_body_and_attachments(payload: dict) -> tuple[str, list[dict]]:
    """Recursively extract text body and attachment metadata from a MIME payload."""

    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[dict] = []

    def _walk_parts(part: dict) -> None:
        filename = part.get("filename", "")
        body_info = part.get("body", {})
        attachment_id = body_info.get("attachmentId")
        mime_type = part.get("mimeType", "")

        # Record attachment if filename or attachmentId exists
        if filename or attachment_id:
            attachments.append(
                {
                    "id": attachment_id or "",
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": body_info.get("size", 0),
                }
            )

        # Record text content if present (and not an attachment with filename)
        data = body_info.get("data")
        if data and not filename:
            try:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                if mime_type == "text/plain":
                    plain_parts.append(decoded)
                elif mime_type == "text/html":
                    html_parts.append(decoded)
            except Exception:
                pass

        # Recurse into nested MIME parts
        for subpart in part.get("parts", []):
            _walk_parts(subpart)

    _walk_parts(payload)

    # Prefer plain text, fallback to html converted to text
    if plain_parts:
        body_text = "\n".join(plain_parts).strip()
    elif html_parts:
        raw_html = "\n".join(html_parts)
        soup = BeautifulSoup(raw_html, "html.parser")
        for element in soup(["script", "style"]):
            element.extract()
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        body_text = "\n".join(line for line in lines if line)
    else:
        body_text = ""

    return body_text, attachments


def read_email(message_id: str) -> dict | None:
    """Fetch full Gmail message by ID and return clean email dictionary."""

    credentials = authenticate_gmail()

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    try:
        message_data = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )
    except HttpError as error:
        if error.resp.status == 404:
            print(f"Message not found: {message_id}")
            return None
        print(f"Gmail API error fetching message {message_id}: {error}")
        return None
    except Exception as error:
        print(f"Error fetching message {message_id}: {error}")
        return None

    payload = message_data.get("payload", {})
    headers = payload.get("headers", [])

    body, attachments = _extract_body_and_attachments(payload)

    return {
        "id": message_data.get("id", message_id),
        "thread_id": message_data.get("threadId", ""),
        "from": get_header(headers, "From"),
        "to": get_header(headers, "To", default=""),
        "cc": get_header(headers, "Cc", default=""),
        "subject": get_header(headers, "Subject"),
        "date": get_header(headers, "Date"),
        "body": body,
        "attachments": attachments,
    }