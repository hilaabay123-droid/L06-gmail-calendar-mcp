# gmail-calendar MCP server

A Python MCP server (official MCP SDK, FastMCP) that gives an MCP client
read access to Gmail, the ability to write **drafts**, and access to Google Calendar.
It runs with `uv` over the **stdio** transport.

## Tools

| Tool | What it does |
|---|---|
| `search_emails(query, max_results=10)` | Searches Gmail using Gmail search syntax and returns the id, sender, subject, date and snippet of each match (at most 50). |
| `read_email(message_id)` | Returns one message's headers and its plain-text body. |
| `create_draft(to, subject, body)` | Saves a Gmail **draft**. The draft is never sent. |
| `list_events(days_ahead=7)` | Lists events on the primary calendar from now until `days_ahead` days from now. |
| `find_free_slots(date, duration_minutes=30)` | Lists free slots of at least the given length on `YYYY-MM-DD`, between 09:00 and 18:00. |
| `create_event(title, start, end, description="")` | Creates a calendar event. Invitations are not sent (`sendUpdates="none"`). |

No tool sends or deletes anything.
All times use **Asia/Jerusalem**. A `start` or `end` without an offset, such as `2026-12-01T14:30`, is read as Jerusalem time.

## Credentials (never stored in this project)

The server reuses an existing OAuth client and `token.json`, both kept in a
private folder outside this project:

```
C:\privet-google-client\
    client_secret_mygoogle.com.json
    token.json
```

The server reads that folder's path from the **`GOOGLE_PRIVATE_DIR`** environment variable.

- `token.json` is loaded with **the scopes it already has**. The server never asks for new ones.
- If the access token has expired, the server refreshes it with the refresh token and saves the new token back into the private `token.json`.
- The server **never opens a browser** and never runs an OAuth flow. If the token is revoked, or a scope a tool needs is missing, the tool returns a clear error that names the scopes it accepts. You then need to re-authorize outside this server.
- Secrets are never printed or logged. `.gitignore` excludes `token.json`, `client_secret_mygoogle.com.json`, `credentials.json` and `.env`.

Scopes each tool accepts (one from each list is enough):

- `search_emails`, `read_email`: `gmail.readonly`, `gmail.modify` or `https://mail.google.com/`
- `create_draft`: `gmail.compose`, `gmail.modify` or `https://mail.google.com/`
- `list_events`, `find_free_slots`: `calendar`, `calendar.readonly`, `calendar.events`, `calendar.events.readonly` or `calendar.events.owned`
- `create_event`: `calendar`, `calendar.events` or `calendar.events.owned`

## Run it

Requirements: Python 3.10 or later and [uv](https://docs.astral.sh/uv/).

```powershell
cd C:\biu\008
uv sync                                          # install dependencies into .venv
$env:GOOGLE_PRIVATE_DIR = "C:\privet-google-client"
uv run server.py                                 # waits for an MCP client on stdin/stdout
```

To try the tools interactively in the MCP Inspector:

```powershell
$env:GOOGLE_PRIVATE_DIR = "C:\privet-google-client"
uv run mcp dev server.py
```

### Register with Claude Code

```powershell
claude mcp add gmail-calendar --env GOOGLE_PRIVATE_DIR=C:\privet-google-client -- uv --directory C:\biu\008 run server.py
```

### Register with Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "gmail-calendar": {
      "command": "uv",
      "args": ["--directory", "C:\\biu\\008", "run", "server.py"],
      "env": { "GOOGLE_PRIVATE_DIR": "C:\\privet-google-client" }
    }
  }
}
```

## Files

- `server.py`: creates the FastMCP server `gmail-calendar` and runs it over stdio
- `google_auth.py`: loads and refreshes credentials, checks scopes and turns API errors into clear messages
- `gmail_tools.py`: the Gmail tools
- `calendar_tools.py`: the Calendar tools
