"""Tests for _extract_body_and_attachments — edge cases for MIME parsing."""

import base64

from mcp_server.reader import _extract_body_and_attachments


def _b64(text: str) -> str:
    """Helper — URL-safe base64 encode a string."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


def test_plain_text_only():
    """Simple message with only a text/plain body."""
    payload = {
        "mimeType": "text/plain",
        "body": {"data": _b64("Hello, world!")},
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert body == "Hello, world!"
    assert attachments == []


def test_html_only_strips_scripts_and_styles():
    """HTML-only message strips <script> and <style> tags."""
    html = "<html><head><style>body{color:red}</style></head><body><p>Content</p><script>alert(1)</script></body></html>"
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64(html)},
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert "Content" in body
    assert "alert" not in body
    assert "color:red" not in body


def test_multipart_alternative_prefers_plain_text():
    """multipart/alternative with both plain and HTML prefers plain text."""
    payload = {
        "mimeType": "multipart/alternative",
        "body": {},
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64("Plain version")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": _b64("<p>HTML version</p>")},
            },
        ],
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert body == "Plain version"
    assert "HTML version" not in body


def test_deeply_nested_multipart_mixed():
    """Deeply nested multipart/mixed + multipart/alternative."""
    payload = {
        "mimeType": "multipart/mixed",
        "body": {},
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "body": {},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": _b64("Nested plain text")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": _b64("<b>Nested HTML</b>")},
                    },
                ],
            },
            {
                "mimeType": "application/pdf",
                "filename": "report.pdf",
                "body": {"attachmentId": "att_001", "size": 12345},
            },
        ],
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert body == "Nested plain text"
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "report.pdf"
    assert attachments[0]["id"] == "att_001"
    assert attachments[0]["size"] == 12345


def test_attachment_with_id_but_no_filename():
    """Attachment with attachmentId but empty filename is still recorded."""
    payload = {
        "mimeType": "multipart/mixed",
        "body": {},
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64("Message body")},
            },
            {
                "mimeType": "image/png",
                "filename": "",
                "body": {"attachmentId": "inline_img_1", "size": 500},
            },
        ],
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert body == "Message body"
    assert len(attachments) == 1
    assert attachments[0]["id"] == "inline_img_1"
    assert attachments[0]["mime_type"] == "image/png"


def test_empty_payload_returns_empty_body():
    """Payload with no body data and no parts returns empty string."""
    payload = {
        "mimeType": "text/plain",
        "body": {},
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert body == ""
    assert attachments == []


def test_multiple_plain_parts_concatenated():
    """Multiple text/plain parts are joined with newlines."""
    payload = {
        "mimeType": "multipart/mixed",
        "body": {},
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64("Part one")},
            },
            {
                "mimeType": "text/plain",
                "body": {"data": _b64("Part two")},
            },
        ],
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert "Part one" in body
    assert "Part two" in body


def test_inline_image_not_treated_as_text():
    """Inline images with filename should not appear in body text."""
    payload = {
        "mimeType": "multipart/related",
        "body": {},
        "parts": [
            {
                "mimeType": "text/html",
                "body": {"data": _b64("<p>See image below</p>")},
            },
            {
                "mimeType": "image/jpeg",
                "filename": "photo.jpg",
                "body": {
                    "attachmentId": "img_att_1",
                    "size": 2048,
                    "data": _b64("fake-image-bytes"),
                },
            },
        ],
    }
    body, attachments = _extract_body_and_attachments(payload)
    assert "See image below" in body
    assert "fake-image-bytes" not in body
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "photo.jpg"
