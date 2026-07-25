import json
import sys

# Ensure UTF-8 output formatting on Windows console
sys.stdout.reconfigure(encoding="utf-8")

from mcp_server.gmail_client import send_email

# Test 1: Invalid email address (Validation Test)
print("=== Test 1: Invalid Recipient Address ===")
res1 = send_email(to="not-an-email", subject="Test", body="Hello")
print(json.dumps(res1, indent=2))

# Test 2: Send a real email to yourself
# (Note: Browsers will pop up for OAuth approval if token.json is not yet authorized for gmail.modify)
recipient = "mavis9982@gmail.com"
print(f"\n=== Test 2: Sending Test Email to {recipient} ===")

res2 = send_email(
    to=recipient,
    subject="MenaDevs email Assistant - Test Email",
    body="",
    cc="mavis60606@gmail.com",
)

print(json.dumps(res2, indent=2))