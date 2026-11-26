"""Gmail tools: search, read and create drafts. Nothing here sends or deletes mail."""
import base64
import html
import re
from email.message import EmailMessage

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from google_auth import google_service, run

_G = "https://www.googleapis.com/auth/"
READ_SCOPES = {_G + "gmail.readonly", _G + "gmail.modify", "https://mail.google.com/"}
DRAFT_SCOPES = {_G + "gmail.compose", _G + "gmail.modify", "https://mail.google.com/"}
MAX_BODY_CHARS = 20000


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _find_part(payload: dict, mime: str) -> str | None:
    if payload.get("mimeType") == mime and payload.get("body", {}).get("data"):
        return payload["body"]["data"]
    for part in payload.get("parts") or []:
        found = _find_part(part, mime)
        if found:
            return found
    return None


def _body_text(payload: dict) -> str:
    plain = _find_part(payload, "text/plain")
    if plain:
        return _decode(plain)
    rich = _find_part(payload, "text/html")
    if rich:
        text = re.sub(r"(?is)<(script|style).*?</\1>", "", _decode(rich))
        return html.unescape(re.sub(r"<[^>]+>", " ", text)).strip()
    return ""


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def search_emails(query: str, max_results: int = 10) -> list[dict]:
        """Search Gmail with Gmail search syntax (e.g. 'from:bob is:unread') and return
        the matching messages' id, sender, subject, date and snippet."""
        max_results = max(1, min(int(max_results), 50))
        gmail = google_service("gmail", "v1", READ_SCOPES, "search emails")
        found = run(
            gmail.users().messages().list(userId="me", q=query, maxResults=max_results),
            "search emails",
        )
        results = []
        for item in found.get("messages", []):
            msg = run(
                gmail.users().messages().get(
                    userId="me", id=item["id"], format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                ),
                "read email metadata",
            )
            headers = msg.get("payload", {}).get("headers", [])
            results.append({
                "id": msg["id"],
                "from": _header(headers, "From"),
                "subject": _header(headers, "Subject"),
                "date": _header(headers, "Date"),
                "snippet": html.unescape(msg.get("snippet", "")),
            })
        return results

    @mcp.tool()
    def read_email(message_id: str) -> dict:
        """Read one Gmail message by its id and return its headers and plain-text body."""
        gmail = google_service("gmail", "v1", READ_SCOPES, "read an email")
        msg = run(gmail.users().messages().get(userId="me", id=message_id, format="full"),
                  "read an email")
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body = _body_text(payload)
        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": _header(headers, "From"),
            "to": _header(headers, "To"),
            "cc": _header(headers, "Cc"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "labels": msg.get("labelIds", []),
            "body": body[:MAX_BODY_CHARS],
            "body_truncated": len(body) > MAX_BODY_CHARS,
        }

    @mcp.tool()
    def create_draft(to: str, subject: str, body: str) -> dict:
        """Create a Gmail DRAFT (it is NOT sent). Review and send it yourself in Gmail."""
        if not to.strip():
            raise ToolError("'to' must contain at least one email address.")
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        gmail = google_service("gmail", "v1", DRAFT_SCOPES, "create a draft")
        draft = run(gmail.users().drafts().create(userId="me", body={"message": {"raw": raw}}),
                    "create a draft")
        return {"draft_id": draft["id"], "status": "Draft saved. It was NOT sent."}
