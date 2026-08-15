"""Gmail API authentication and service caching.

Handles OAuth 2.0 credential management, token persistence,
and provides a cached Gmail API service instance.
"""

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Module logger — writes to stderr so it never corrupts MCP stdio transport.
logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler()  # defaults to stderr
    _handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.WARNING)

# Full read, search, send, reply, and modify permissions.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

# Cached Gmail API service instance.
_cached_service = None


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


def get_service():
    """Return a cached Gmail API service, rebuilding only when credentials expire."""
    global _cached_service

    if _cached_service is not None:
        # Quick check: if the underlying credentials are still valid, reuse.
        try:
            creds = _cached_service._http.credentials
            if creds and creds.valid:
                return _cached_service
        except AttributeError:
            pass

    credentials = authenticate_gmail()
    _cached_service = build("gmail", "v1", credentials=credentials)
    return _cached_service
