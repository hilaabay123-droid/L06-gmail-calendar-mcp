"""Create token.json for the gmail-calendar MCP server (run once, by hand).

    uv run scripts/create_token.py

Runs the Google OAuth sign-in in your browser with the client file in
GOOGLE_PRIVATE_DIR and saves token.json in that same folder. Only this script
opens a browser; the MCP server never does. Secrets are never printed.
"""
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# Minimal permissions: write drafts, read mail, manage events. No gmail.modify,
# no gmail.send, no full calendar access.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]
CLIENT_FILE = "client_secret_mygoogle.com.json"
TOKEN_FILE = "token.json"


def main() -> None:
    value = os.environ.get("GOOGLE_PRIVATE_DIR")
    if not value:
        sys.exit("GOOGLE_PRIVATE_DIR is not set. Point it at the folder that holds the client file.")
    folder = Path(value)
    client = folder / CLIENT_FILE
    if not client.is_file():
        sys.exit(f"Client file not found: {CLIENT_FILE} in GOOGLE_PRIVATE_DIR.")

    flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
    print("Opening the browser for Google sign-in. Approve all requested permissions.", flush=True)
    # Empty prompt: the library would otherwise print the sign-in URL, which includes the client ID.
    creds = flow.run_local_server(port=0, open_browser=True, authorization_prompt_message="")

    granted = set(creds.scopes or [])
    missing = [s for s in SCOPES if s not in granted]
    if missing:
        short = ", ".join(s.rsplit("/", 1)[-1] for s in missing)
        sys.exit(f"Not saved: these permissions were not granted: {short}. Run the script again "
                 "and tick every box on the consent screen.")

    (folder / TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
    print(f"Saved {TOKEN_FILE} in GOOGLE_PRIVATE_DIR with scopes: "
          + ", ".join(sorted(s.rsplit("/", 1)[-1] for s in granted)))


if __name__ == "__main__":
    main()
