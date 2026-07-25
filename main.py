from mcp_server.gmail_client import list_emails,reply_to_email
import json
import sys

# Ensure UTF-8 output formatting on Windows console
sys.stdout.reconfigure(encoding="utf-8")

from mcp_server.gmail_client import send_email

# Test 1: Invalid email address (Validation Test)
print("=== reply email ===")
res1 = reply_to_email(message_id="19f99cf659c2d8e5",body="")
print(json.dumps(res1, indent=2))

