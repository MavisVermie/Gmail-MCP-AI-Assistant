from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Read-only access for now.
# Later, we will expand this so the app can send and reply.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BASE_DIR = Path(__file__).resolve().parent
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
                    "credentials.json was not found. "
                    "Download it from Google Cloud and place it beside main.py."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )

            credentials = flow.run_local_server(port=0)

        # Save the token so login is not required every time.
        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials


def get_header(headers: list[dict], header_name: str) -> str:
    """Find one header, such as Subject or From."""

    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")

    return "Unknown"


def print_latest_emails(max_results: int = 5) -> None:
    """Print basic information about the newest Gmail messages."""

    credentials = authenticate_gmail()

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            maxResults=max_results,
        )
        .execute()
    )

    messages = response.get("messages", [])

    if not messages:
        print("No emails were found.")
        return

    print("\nLatest emails:\n")

    for index, message in enumerate(messages, start=1):
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

        sender = get_header(headers, "From")
        subject = get_header(headers, "Subject")
        date = get_header(headers, "Date")
        snippet = message_data.get("snippet", "")

        print(f"{index}. {subject}")
        print(f"   From: {sender}")
        print(f"   Date: {date}")
        print(f"   Preview: {snippet}")
        print()


def main() -> None:
    try:
        print_latest_emails(max_results=5)

    except FileNotFoundError as error:
        print(f"\nSetup error: {error}")

    except HttpError as error:
        print(f"\nGmail API error: {error}")

    except Exception as error:
        print(f"\nUnexpected error: {error}")


if __name__ == "__main__":
    main()