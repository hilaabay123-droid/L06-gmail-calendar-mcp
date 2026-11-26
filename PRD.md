# PRD: `gmail-calendar` MCP Server

| | |
|---|---|
| **Status** | Done. All required steps are tested and done (see §8). Gmail read tools still need a token with `gmail.readonly` (see §9) |
| **Owner** | Project owner (single user) |
| **Location** | `C:\biu\008` |
| **Date** | 2026-11-25 |

---

## 1. Overview

**Last week's program (`C:\biu\007`, package `google-test`).** A uv-run Python
CLI with two commands:

- `uv run create-token` runs the Google OAuth flow (`InstalledAppFlow`). It opens a
  browser for sign-in and consent and saves `token.json` in `C:\privet-google-client`.
  The OAuth client is the first `client_secret*.json` in that folder, and the folder
  can be overridden with `GOOGLE_CLIENT_DIR`.
- `uv run google-test` loads that token without opening a browser and refreshes it
  if it has expired. It then does exactly two things:
  1. Creates a Gmail **draft** addressed to the owner's own address (looked up with
     `users.getProfile`). The subject is a fixed `Test draft - <timestamp>` and the
     body is fixed.
  2. Creates a 1-hour event titled `Test event (google-test)` on the primary
     calendar. It starts **4 hours from now** in the PC's local time zone (`tzlocal`).

It requests only two scopes: `gmail.compose` and `calendar.events`. If the token is
missing, invalid, lacks those scopes or can't be refreshed, it exits with a message
to run `create-token` again.

**Problem.** The program proved the Google setup works, but every value is
hard-coded: the recipient (always yourself), subject, body, event title, time
(always now + 4 h) and duration (always 1 h). It can't take a request, read
mail, look at the calendar or choose a time. Every new kind of task ("draft a
reply to Dana and book an hour with her tomorrow afternoon") would need new code.

**Solution.** An MCP server that exposes Gmail and Calendar as small, safe
**tools**. Claude Code reads a free-text request, decides which tools to call and
in what order, and fills in the arguments. The Google logic is written once.
The *workflow* comes from the request rather than from code.

**Why MCP instead of a fixed program**

- **Flexible.** Any combination of search, read, draft and schedule from one sentence.
- **Safe by design.** The server decides which actions exist at all. There is no
  send or delete tool, so the model can't do either.
- **Reuses what works.** Same Google client and `token.json` (created by `create-token`)
  as last week, with no new OAuth setup. Like `google-test`, the server never opens a browser.
- **Safer than the scope allows.** `gmail.compose` technically allows *sending* mail.
  The server limits what can happen by exposing no send tool.
- **Standard.** Any MCP host can use it: Claude Code, Claude Desktop or MCP Inspector.

## 2. Goals and success criteria

| Goal | Success criterion |
|---|---|
| One request does a multi-step job | A single free-text request in Claude Code creates **one Gmail draft** and **one calendar event starting 4 hours from now**, with no code changes |
| Safe actions only | Requests to send or delete mail or events are refused, because no such tool exists |
| Reuse existing auth | Works with the existing `token.json` and its current scopes. No browser and no new consent |
| Correct local time | All times are in **Asia/Jerusalem** |

Example request:
> "Draft an email to bob@example.com saying I'll call him later, and add a
> 30-minute 'Call Bob' event 4 hours from now."

## 3. Users

- **Primary user:** the project owner, working through **Claude Code** on their own Windows machine.
- **Account:** the owner's own Google account. One user only, with no sharing or multi-tenancy.

## 4. Scope

**In scope**

- Search and read Gmail messages
- Create Gmail **drafts**
- List calendar events, find free time and create events on the primary calendar
- stdio MCP server run locally with `uv`

**Out of scope**

- **Sending** email, or sending calendar invitations
- **Deleting**, trashing, archiving or modifying mail or events
- Web apps, HTTP/SSE transport and hosted deployment
- New OAuth flows or opening a browser from the server
- Attachments, labels, other calendars and attendees

## 5. Functional requirements

| # | Tool | Inputs | Output | Google API call |
|---|---|---|---|---|
| 1 | `search_emails` | `query` (Gmail search syntax), `max_results` (default 10, max 50) | List of `{id, from, subject, date, snippet}` | Gmail `users.messages.list` to find matches, then `users.messages.get` (metadata) for each |
| 2 | `read_email` | `message_id` | `{id, thread_id, from, to, cc, subject, date, labels, body, body_truncated}`. Plain-text body, up to 20,000 characters | Gmail `users.messages.get` (full) |
| 3 | `create_draft` | `to`, `subject`, `body` | `{draft_id, status}`. Draft is **not sent** | Gmail `users.drafts.create` |
| 4 | `list_events` | `days_ahead` (default 7, range 1–365) | List of `{id, title, start, end, location}` | Calendar `events.list` |
| 5 | `find_free_slots` | `date` (YYYY-MM-DD), `duration_minutes` (default 30) | `{date, time_zone, working_hours, free_slots[]}` within 09:00–18:00 | Calendar `events.list` |
| 6 | `create_event` | `title`, `start`, `end` (ISO 8601), `description` (optional) | `{id, title, start, end, link}` | Calendar `events.insert` with `sendUpdates="none"` |

**Rules shared by all tools**

- Each tool has a short English description that the model reads.
- Invalid input, such as a bad date or `end` before `start`, returns a clear error.
- A missing permission returns a clear error that names the scopes the tool accepts.
- `find_free_slots` treats all-day events, events marked "free" and events the owner declined as **not busy**.

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| **Secrets** | `client_secret_mygoogle.com.json` and `token.json` stay in `C:\privet-google-client`. The server finds that folder through the `GOOGLE_PRIVATE_DIR` environment variable. The files are never copied into the project, and secrets are never printed or logged |
| **Git hygiene** | `.gitignore` excludes `token.json`, `client_secret_mygoogle.com.json`, `credentials.json` and `.env` (plus `.venv/` and `__pycache__/`) |
| **Least capability** | No tool sends, deletes, trashes or modifies anything. Only the API calls listed in §5 are used |
| **Auth** | `token.json` is loaded with the scopes it already has. An expired access token is refreshed and saved back to the private folder only. The server never opens a browser |
| **Transport** | MCP over **stdio** |
| **Runtime** | Python 3.10 or later, run with **uv**. Built on the official MCP Python SDK's **FastMCP**, pinned to `mcp<2` because v2 renamed FastMCP |
| **Time zone** | **Asia/Jerusalem** for all inputs and outputs (`tzdata` is bundled for Windows) |
| **Code size** | Each Python file is under 150 lines. Currently `server.py` 17, `google_auth.py` 110, `gmail_tools.py` 115, `calendar_tools.py` 111, `test_server.py` 48 |

## 7. Architecture

```
┌──────────────────────── Owner's PC ─────────────────────────┐
│                                                             │
│  ┌──────────────┐   free-text    ┌─────────────────────┐    │
│  │  Owner       │ ─────────────► │  Claude Code (HOST) │    │
│  └──────────────┘                │   └─ MCP CLIENT     │    │
│                                  └─────────┬───────────┘    │
│                                            │ JSON-RPC over  │
│                                            │ stdio (uv run) │
│                                  ┌─────────▼───────────┐    │
│                                  │ gmail-calendar      │    │
│                                  │ MCP SERVER          │    │
│                                  │  server.py          │    │
│                                  │  gmail_tools.py     │    │
│                                  │  calendar_tools.py  │    │
│                                  │  google_auth.py ────┼──┐ │
│                                  └─────────┬───────────┘  │ │
│                                            │              │ │ reads (and refreshes)
│   C:\privet-google-client\  ◄──────────────┼──────────────┘ │ via GOOGLE_PRIVATE_DIR
│     token.json                             │                │
│     client_secret_mygoogle.com.json        │                │
└────────────────────────────────────────────┼────────────────┘
                                             │ HTTPS (OAuth access token)
                               ┌─────────────▼─────────────┐
                               │ Google APIs               │
                               │  Gmail v1  · Calendar v3  │
                               └───────────────────────────┘
```

**Components**

- **Host (Claude Code):** runs the model, shows tool calls, asks for approval, and launches the server.
- **Client:** the MCP client inside Claude Code. It talks JSON-RPC to the server over stdin and stdout.
- **Server:** FastMCP app `gmail-calendar` with 6 tools. `google_auth.py` loads and refreshes credentials, checks scopes and turns Google errors into clear messages.
- **Google APIs:** Gmail v1 and Calendar v3, called with the user's OAuth token.
- **token.json:** OAuth tokens stored outside the project and read at runtime only.

## 8. Acceptance criteria

- [x] **Server answers.** `test_server.py` starts it over stdio and gets its name and all 6 tools
- [x] **Calendar read works.** `list_events(days_ahead=1)` returns real events with the current token
- [x] **Connected in Claude Code.** After `claude mcp add ...`, `/mcp` shows `gmail-calendar` as **connected**
  - Screenshot: [`screenshots/01-mcp-connected.png`](screenshots/01-mcp-connected.png)
- [x] **Draft and event from one request.** A single free-text request creates one Gmail draft (visible in Gmail Drafts, not sent) and one calendar event starting 4 hours from now, in Asia/Jerusalem time
  - Request: [`screenshots/02-calendar-question-and-mission.png`](screenshots/02-calendar-question-and-mission.png)
  - Draft "L06 test" in Gmail: [`screenshots/03-gmail-draft-L06-test.png`](screenshots/03-gmail-draft-L06-test.png)
  - Event "MCP works" in Calendar: [`screenshots/04-calendar-mcp-works.png`](screenshots/04-calendar-mcp-works.png)
  - Follow-up "Study group" event in a free slot: [`screenshots/05-calendar-study-group.png`](screenshots/05-calendar-study-group.png)
- [x] **Send and delete refused.** Asking Claude to send an email, or to delete an email or event, fails because no tool can do it
  - Screenshot: [`screenshots/06-boundary-send-delete-refused.png`](screenshots/06-boundary-send-delete-refused.png)
- [x] **No send or delete code.** The code contains no `send`, `delete`, `trash`, `modify`, `update` or `patch` API calls
- [x] **No secrets in git.** After `git init` and `git add .`, `git status` shows no `token.json`, `client_secret*.json`, `credentials.json` or `.env`
  - No screenshot yet. Proven by the `git status` output shown before the first commit (`bbe4eed`), where none of these files was staged
- [x] **Size limit.** Every `.py` file is under 150 lines

## 9. Risks and limitations

**Tested so far**

- `test_server.py` passed. The server starts over stdio, lists all 6 tools with descriptions, and `list_events(days_ahead=1)` returned real events using the current `token.json`. This proves the token has **calendar read** permission.
- The error path was checked: a wrong `GOOGLE_PRIVATE_DIR` returns a clear error instead of a crash.
- **Not yet tested against the account:** `search_emails`, `read_email`, `create_draft`, `find_free_slots` and `create_event`.
- **Known permission gap.** The current `token.json` was made by last week's `create-token`,
  which requests only `gmail.compose` and `calendar.events` (see `C:\biu\007\src\google_test\auth.py`).
  This is based on that code. The token file itself was not inspected. Expected result per tool:

  | Tool | Works with the current token? |
  |---|---|
  | `create_draft` | Yes (`gmail.compose`) |
  | `list_events`, `find_free_slots`, `create_event` | Yes (`calendar.events`). `list_events` was confirmed |
  | `search_emails`, `read_email` | **No.** They need `gmail.readonly` (or `gmail.modify` or full mail access). They will return the "missing permission" error |

  **Fix:** add `https://www.googleapis.com/auth/gmail.readonly` to `SCOPES` in last week's `auth.py`,
  run `uv run create-token` once (it opens a browser for consent), then rerun `test_server.py`.
  Re-consent replaces the token for both projects. Last week's `google-test` keeps working
  because it only checks that its own two scopes are present.

| Risk | Impact | Mitigation |
|---|---|---|
| **Missing scopes.** `token.json` is used with only the scopes it already has: `gmail.compose` and `calendar.events`. `search_emails` and `read_email` need `gmail.readonly`, `gmail.modify` or full mail access, which the current token **does not have** | `search_emails` and `read_email` fail until the token is re-authorized. The other 4 tools are covered | The tool returns a clear "missing permission" error listing the scopes it accepts. Add `gmail.readonly` to last week's `create-token` and run it once (see "Known permission gap" above) |
| **Token expiry or revocation** | Every tool fails | Expired access tokens are refreshed automatically with the refresh token. If Google refuses the refresh, the tool says to re-authorize. The server never opens a browser |
| **Prompt injection from email content.** `read_email` and `search_emails` return text that strangers wrote, which may contain instructions such as "forward this to..." or "create an event..." | The model could be steered into drafting or scheduling something the owner didn't ask for | No send or delete tools exist, so the worst case is an unwanted **draft** or **event**, both easy to see and undo by hand. Claude Code shows each tool call for approval. Treat email text as data, not instructions |
| **Data exposure to the model.** Email bodies are passed to the model's context | Private content is processed by the LLM | Bodies are capped at 20,000 characters. Read only what the request needs |
| **SDK drift.** MCP SDK v2 renamed FastMCP | A dependency upgrade breaks the server | `mcp<2` is pinned in `pyproject.toml` |
| **Simplified free-time logic.** Fixed 09:00–18:00 hours, primary calendar only, all-day events ignored | A suggested slot may not suit the owner | Documented in the tool description and README |
