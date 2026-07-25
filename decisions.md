# Architectural & Technical Decisions

This document explains the main design decisions made during the project and why they were chosen.

---

## 1. Chose Gmail API

**Decision**

I used the Gmail API instead of Microsoft Graph.

**Why**

I am more familiar with Google's services, and the Gmail API has excellent Python documentation and examples, making development and testing much easier.

---

## 2. Separated the Gmail Client from the MCP Server

**Decision**

I kept all Gmail-related logic inside `gmail_client.py` and exposed it through `server.py`.

**Why**

This keeps the project organized and separates responsibilities. If I ever change from Gmail to another email provider, most of the changes would only be inside the Gmail client.

---

## 3. Returned Clean Data Instead of Raw Gmail Responses

**Decision**

The Gmail client returns simple dictionaries instead of the complete Gmail API response.

**Why**

The Gmail API returns a large amount of unnecessary information. Returning only the required fields makes the agent easier to work with and reduces complexity.

---

## 4. Used Pydantic AI with FastMCP

**Decision**

I chose Pydantic AI for the AI agent and FastMCP for the MCP server.

**Why**

Pydantic AI provides native MCP support and works well with typed Python code. FastMCP makes it simple to expose Python functions as MCP tools with minimal boilerplate.

---

## 5. Added User Confirmation Before Sending Emails

**Decision**

The application always asks the user for confirmation before calling `send_email()` or `reply_to_email()`.

**Why**

This prevents accidental emails from being sent and gives the user an opportunity to review the message before it is delivered.

---

## 6. Used OAuth Authentication

**Decision**

The application authenticates with Gmail using Google's OAuth 2.0 flow.

**Why**

OAuth is Google's recommended authentication method. It is more secure than storing passwords and allows the application to reuse saved credentials without requiring the user to sign in every time.

---

## 7. Added Tool Logging

**Decision**

Every MCP tool call is logged.

**Why**

Logging makes debugging easier and provides a simple record of which tools were executed, whether they succeeded, and how long they took to complete.

---
## 8. Validated Emails Before Sending

**Decision**

The application does not allow sending an email if the recipient is invalid or if the subject or body is empty.

**Why**

This helps prevent accidental or incomplete emails from being sent. Validating the input before calling the Gmail API also avoids unnecessary API requests and provides clearer feedback to the user.