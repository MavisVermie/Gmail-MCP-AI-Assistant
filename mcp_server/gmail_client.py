"""Gmail client — public API surface.

Re-exports all Gmail operations from their respective modules
so that existing imports (``from mcp_server.gmail_client import …``)
continue to work without modification.
"""

# Auth
from mcp_server.auth import authenticate_gmail  # noqa: F401

# Read operations
from mcp_server.reader import (  # noqa: F401
    get_header,
    list_emails,
    search_emails,
    read_email,
)

# Write operations
from mcp_server.sender import (  # noqa: F401
    _validate_email,
    _normalize_recipients,
    send_email,
    reply_to_email,
)

# Label & thread operations
from mcp_server.labels import (  # noqa: F401
    list_labels,
    modify_labels,
    get_thread,
)