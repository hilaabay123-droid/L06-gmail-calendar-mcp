"""Load Google credentials from GOOGLE_PRIVATE_DIR.

The files stay in the private folder: they are never copied, printed or logged,
and this module never starts an OAuth flow or opens a browser.
"""
import json
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp.exceptions import ToolError

TOKEN_FILE = "token.json"
CLIENT_FILE = "client_secret_mygoogle.com.json"
REAUTH_HINT = (
    "Run 'uv run scripts/create_token.py' once to sign in again and save a new token.json "
    "(this server never opens a browser)."
)

_creds: Credentials | None = None


def _private_dir() -> Path:
    value = os.environ.get("GOOGLE_PRIVATE_DIR")
    if not value:
        raise ToolError("GOOGLE_PRIVATE_DIR is not set. Point it at the folder that holds token.json.")
    folder = Path(value)
    if not folder.is_dir():
        raise ToolError(f"GOOGLE_PRIVATE_DIR is not an existing folder: {folder}")
    return folder


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ToolError(f"Could not read {path.name} in GOOGLE_PRIVATE_DIR (missing or not valid JSON).")


def _load_credentials() -> Credentials:
    folder = _private_dir()
    info = _read_json(folder / TOKEN_FILE)
    if not (info.get("client_id") and info.get("client_secret")):
        client = _read_json(folder / CLIENT_FILE)
        section = client.get("installed") or client.get("web") or {}
        info["client_id"] = info.get("client_id") or section.get("client_id")
        info["client_secret"] = info.get("client_secret") or section.get("client_secret")
    try:
        # No scopes argument: use exactly the scopes already stored in token.json.
        return Credentials.from_authorized_user_info(info)
    except ValueError:
        raise ToolError(f"token.json is missing required fields (e.g. refresh_token). {REAUTH_HINT}")


def _save_refreshed_token(creds: Credentials) -> None:
    """Write the new access token back into the private token.json only."""
    path = _private_dir() / TOKEN_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["token"] = creds.token
        if creds.expiry:
            data["expiry"] = creds.expiry.isoformat() + "Z"
        path.write_text(json.dumps(data), encoding="utf-8")
    except (OSError, ValueError):
        pass  # The in-memory token still works for this session.


def get_credentials() -> Credentials:
    global _creds
    if _creds is None:
        _creds = _load_credentials()
    if not _creds.valid:
        if not _creds.refresh_token:
            raise ToolError(f"token.json has expired and has no refresh token. {REAUTH_HINT}")
        try:
            _creds.refresh(Request())
        except RefreshError:
            _creds = None
            raise ToolError(f"Google refused to refresh token.json (expired or revoked). {REAUTH_HINT}")
        _save_refreshed_token(_creds)
    return _creds


def google_service(api: str, version: str, accepted_scopes: set[str], action: str):
    """Build an API client, failing clearly if token.json lacks a needed scope."""
    creds = get_credentials()
    granted = set(creds.scopes or [])
    if granted and not granted & accepted_scopes:
        raise ToolError(
            f"Missing Google permission to {action}. token.json needs one of these scopes: "
            f"{', '.join(sorted(accepted_scopes))}. {REAUTH_HINT}"
        )
    return build(api, version, credentials=creds, cache_discovery=False)


def run(request, action: str):
    """Execute a Google API request and turn HTTP errors into clear messages."""
    try:
        return request.execute()
    except HttpError as err:
        status = err.resp.status
        reason = getattr(err, "reason", "") or ""
        if status == 403 and ("insufficient" in reason.lower() or "scope" in reason.lower()):
            raise ToolError(f"Missing Google permission to {action}. {REAUTH_HINT}")
        if status == 401:
            raise ToolError(f"Google rejected the credentials while trying to {action}. {REAUTH_HINT}")
        if status == 404:
            raise ToolError(f"Not found while trying to {action}. Check the ID you passed.")
        raise ToolError(f"Google API error {status} while trying to {action}: {reason}")
