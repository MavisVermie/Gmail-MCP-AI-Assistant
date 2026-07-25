# MenaDevs Gmail Assistant (AI Agent + FastMCP)

An intelligent, conversational Gmail assistant built with **Pydantic AI** and **FastMCP**. The application connects over the **Model Context Protocol (MCP)** via `stdio` transport, exposing Gmail operations to an autonomous LLM agent with application-enforced security approvals and structured JSON Lines audit logging.

---

## 🏗️ Architecture Overview

The system uses a decoupled architecture where the AI Agent never interacts directly with Gmail APIs or internal client code. Instead, all email operations flow through an MCP server boundary:

```text
+-----------------------------------------------------------------------------------+
|                                  USER TERMINAL                                    |
|                               (Interactive CLI)                                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                                 PYDANTIC AI AGENT                                 |
|               (LLM Orchestrator: OpenAI gpt-4o + Message History)                |
+-----------------------------------------------------------------------------------+
                                         │
                         Application Security Interceptor
                   (process_tool_approval for send/reply y/N)
                                         │
                                         ▼  MCP stdio Protocol
+-----------------------------------------------------------------------------------+
|                                 FASTMCP SERVER                                    |
|                             (mcp_server/server.py)                                |
|                                                                                   |
|  [list_emails]   [read_email]   [search_emails]   [send_email]   [reply_to_email]  |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼ Python Calls
+-----------------------------------------------------------------------------------+
|                                 GMAIL CLIENT API                                  |
|                          (mcp_server/gmail_client.py)                             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼ OAuth 2.0 / HTTPS
+-----------------------------------------------------------------------------------+
|                                GOOGLE GMAIL API                                   |
|                      (https://gmail.googleapis.com/...)                          |
+-----------------------------------------------------------------------------------+
```

---

## ⚡ 15-Minute Setup & Reviewer Guide

Follow these steps to set up and run the application in under 15 minutes.

### 1. Prerequisites
- **Python 3.10** or higher installed.
- A **Google Cloud Platform (GCP)** project with the **Gmail API** enabled and an **OAuth 2.0 Client ID** configured as a *Desktop Application*.

### 2. Installation
Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/MavisVermie/MenaDevs-Email-Assistant.git
cd MenaDevs-Email-Assistant

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment & Credential Configuration
1. **OpenAI API Key**: Create a `.env` file in the project root containing your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-proj-your-openai-api-key-here
   ```
2. **Google OAuth Credentials**: Download your OAuth client secret JSON file from Google Cloud Console, rename it to `credentials.json`, and place it in the **project root directory**:
   ```text
   MenaDevs-Email-Assistant/
   ├── credentials.json  <-- Place here
   ├── .env
   ├── main.py
   └── ...
   ```

### 4. Running the Agent
Run the main conversational agent:

```bash
python main.py
```

*Note: On your first run, a browser window will automatically open asking you to authorize the Gmail application with `gmail.modify` permissions. After approving, a local `token.json` file is saved for future session reuse.*

---

## 🛠️ Framework & Technology Selection

| Component | Technology | Rationale & Selection Criteria |
| :--- | :--- | :--- |
| **Agent Framework** | **Pydantic AI** | Selected for type-safe tool parameters, native MCP toolset support (`MCPToolset`), robust multi-turn message history tracking (`ModelMessage`), and clean exception management. |
| **MCP Server** | **FastMCP** | Lightweight Python framework that auto-generates MCP tool schemas from type annotations and docstrings, supporting stdio execution without boilerplate. |
| **LLM Model** | **OpenAI `gpt-4o`** | High function-calling reliability, fast response times, and strong adherence to system prompts and structured tool calling workflows. |
| **Email API** | **Google Gmail API** | Official Google client library (`google-api-python-client`) with OAuth 2.0 authentication and standard MIME parsing (`email.mime`). |

---

## 🔒 Key Design & Security Features

- **Decoupled Architecture**: The agent connects to the MCP server strictly over `StdioTransport` subprocess communication without importing internal functions directly.
- **Application-Enforced Security Interceptions**: Calls to `send_email` and `reply_to_email` are intercepted before execution. The CLI presents a full preview box showing recipient, original subject, message ID, and body text, requiring explicit `y/N` confirmation before sending.
- **MIME Parsing & HTML Clean-up**: Automatically parses multipart emails, extracts attachment metadata, and converts HTML-only emails to clean plain text via `BeautifulSoup`.
- **Structured Audit Logging**: Every tool execution is logged in single-line **JSON Lines** format to both console and `agent.log` with execution timing, success/failure flags, and sanitized parameters (masking API keys and truncating email bodies).

---

## ⚠️ Known Limitations

1. **Stdio Subprocess Transport**: Currently relies on local `stdio` subprocess transport rather than an external HTTP/SSE microservice URL.
2. **Single Account Context**: Authenticates a single Gmail inbox per `token.json` session.
3. **Plain Text Composition**: Email creation and replies currently generate UTF-8 plain-text bodies; rich HTML email rendering/editing is not yet supported.
4. **Metadata-Only Attachments**: Attachment metadata is extracted and displayed, but downloading or uploading attachment binary files to disk is not exposed as an MCP tool.

---

## 🔮 Future Enhancements (With More Time)

- **Drafts & Rich Text Support**: Add a `create_draft` MCP tool and support Markdown/HTML email formatting.
- **Attachment Download & Inspection**: Implement an `inspect_attachment(attachment_id)` tool to download and analyze PDF/CSV documents.
- **Real-Time Webhooks / Push Notifications**: Integrate Gmail `watch()` API with Google Cloud Pub/Sub for real-time background email alerts.
- **Remote MCP HTTP/SSE Deployment**: Deploy the FastMCP server as a standalone Dockerized container supporting SSE transport for multi-user web clients.
