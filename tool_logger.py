"""Structured JSON Lines logging for MCP tool invocations.

Logs to both console (stdout) and agent.log file. Sensitive
parameter values (tokens, credentials) are automatically redacted
and long email bodies are truncated.
"""

import datetime
import json
import logging
import sys


# --- Structured Logging Setup (JSON Lines) ---
logger = logging.getLogger("mcp_agent_logger")
logger.setLevel(logging.INFO)
logger.propagate = False

class JSONLinesFormatter(logging.Formatter):
    """Format log records as raw JSON strings."""
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()

_formatter = JSONLinesFormatter()

_file_handler = logging.FileHandler("agent.log", encoding="utf-8")
_file_handler.setFormatter(_formatter)
logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
logger.addHandler(_console_handler)

SENSITIVE_KEYS = {"token", "credentials", "api_key", "secret", "password", "auth", "key"}


def sanitize_params(params: dict) -> dict:
    """Sanitize parameters before logging.

    Masks sensitive credential/token keys and truncates long email bodies.
    """
    if not isinstance(params, dict):
        return {}

    sanitized = {}
    for key, val in params.items():
        if any(s_key in key.lower() for s_key in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif key == "body" and isinstance(val, str):
            if len(val) > 100:
                sanitized[key] = val[:100] + f"... [truncated, len={len(val)}]"
            else:
                sanitized[key] = val
        else:
            try:
                json.dumps(val)
                sanitized[key] = val
            except TypeError:
                sanitized[key] = str(val)
    return sanitized


def log_tool_invocation(
    tool_name: str,
    params: dict,
    success: bool,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Emit a structured JSON Line log entry to console and agent.log."""
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool_name": tool_name,
        "params": sanitize_params(params),
        "success": success,
        "duration_ms": round(duration_ms, 2),
        "error": error,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
