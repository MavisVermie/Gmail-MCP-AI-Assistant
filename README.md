# MenaDevs Gmail Assistant

A CLI email assistant built with Python, Pydantic AI, and FastMCP. It lets you list, read, search, send, and reply to Gmail messages through a terminal chat interface using the Model Context Protocol (MCP).

---

## Features

- Read, search, send, and reply to Gmail messages
- Multi-turn conversation memory
- Human confirmation before sending or replying to emails
- Structured JSON Lines audit logging
- OAuth 2.0 authentication (`https://www.googleapis.com/auth/gmail.modify`)
- MCP communication over stdio

---

## Architecture

```text
+---------------+     Stdio     +---------------+     Python     +--------------+     HTTPS     +-----------+
|  User (CLI)   | ------------> | Pydantic AI   | -------------> | FastMCP      | ------------> | Gmail API |
| Chat Loop     | <------------ | Agent (gpt-4o)| <------------- | Server       | <------------ | (Google)  |
+---------------+               +---------------+                +--------------+               +-----------+
```

The terminal chat loop sends user prompts to a Pydantic AI agent configured with `openai:gpt-4o`. The agent invokes email tools exposed by a FastMCP server running as a subprocess over stdio. The FastMCP server calls the Gmail client, which authenticates via Google OAuth 2.0 and communicates with the Gmail API.

---

## Project Structure

```text
.
├── main.py
├── mcp_server/
│   ├── gmail_client.py
│   └── server.py
├── tests/
│   └── test_gmail_client.py
├── requirements.txt
├── README.md
└── decisions.md
```

---

## Setup

### Requirements
- **Python 3.11+**
- Google Cloud project with the Gmail API enabled
- OpenAI API key

### Installation
Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/MavisVermie/MenaDevs-Email-Assistant.git
cd MenaDevs-Email-Assistant

python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Configuration
1. Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```
2. Download your OAuth client secret from Google Cloud Console, rename it `credentials.json`, and place it in the project root directory.

> **Note on OAuth Scopes:** This project uses the `https://www.googleapis.com/auth/gmail.modify` scope. If you ever update or change OAuth scopes in the code, delete `token.json` and run the application again to re-authenticate.

### Run the Project
Start the interactive CLI:

```bash
python main.py
```

On first run, your browser will open asking you to authorize access to your Gmail account. Once authorized, a `token.json` file is saved locally for future runs.

---

## Running Tests

Run the test suite with pytest:

```bash
pytest -v
```

The unit tests cover header parsing, email validation, and recipient normalization functions in `tests/test_gmail_client.py`.

---

## Example Conversation

```text
You > Show my latest 2 emails.

Assistant > Here are your 2 most recent emails:
1. From: Shasta Smith <shasta@example.com> | Subject: Return | ID: 19f9a22d5769ff92
2. From: Pizza Hut KSA <pizzahut@example.com> | Subject: Special Offer | ID: 19f99e6031c8f290

You > Read the first one.

Assistant > Subject: Return
From: Shasta Smith <shasta@example.com>
Date: Sat, 25 Jul 2026 16:05:00 +0000
Body: Hello! I am needing to return the hardware we purchased...

You > Reply telling them hardware sales are final per our policy.

🔒 [SECURITY APPROVAL REQUIRED: REPLY TO EMAIL]
  • Message ID        : 19f9a22d5769ff92
  • Recipient (To)    : Shasta Smith <shasta@example.com>
  • Original Subject  : Return
  • Reply Body        :
Hello Shasta, per our return policy, hardware physical sales are final.
=================================================================
Do you approve sending this reply? (y/N): y

✅ Reply approved by user. Executing via MCP...

Assistant > I have sent the reply to Shasta Smith.
```

---

## Known Limitations

- Supports one Gmail account per session
- Attachments are listed by metadata but file contents are not downloaded
- CLI only (no web interface)

---

## Future Improvements

- Draft support
- Attachment downloads
- Remote HTTP/SSE transport
- Rich HTML emails
