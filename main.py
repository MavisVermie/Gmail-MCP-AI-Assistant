import json
import sys

# Ensure UTF-8 output formatting on Windows console
sys.stdout.reconfigure(encoding="utf-8")

from mcp_server.gmail_client import search_emails

test_queries = [
    "is:unread",
    "newer_than:7d",
    "subject:login",
    "has:attachment",
    "something-that-does-not-exist-123456",
]

for idx, query in enumerate(test_queries, start=1):
    print(f"\n==========================================")
    print(f"Test {idx}: search_emails(query='{query}')")
    print(f"==========================================")

    results = search_emails(query, max_results=3)
    print(f"Total results returned: {len(results)}")

    for item_idx, email in enumerate(results, start=1):
        print(f"\n  Result {item_idx}:")
        print(f"    ID:        {email['id']}")
        print(f"    Thread ID: {email['thread_id']}")
        print(f"    From:      {email['from']}")
        print(f"    Subject:   {email['subject']}")
        print(f"    Date:      {email['date']}")
        print(f"    Snippet:   {email['snippet'][:80]}...")