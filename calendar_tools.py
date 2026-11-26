"""Google Calendar tools (time zone Asia/Jerusalem). Nothing here deletes events."""
from datetime import date as Date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from google_auth import google_service, run

TZ_NAME = "Asia/Jerusalem"
TZ = ZoneInfo(TZ_NAME)
WORK_START, WORK_END = time(9, 0), time(18, 0)

_C = "https://www.googleapis.com/auth/calendar"
READ_SCOPES = {_C, _C + ".readonly", _C + ".events", _C + ".events.readonly", _C + ".events.owned"}
WRITE_SCOPES = {_C, _C + ".events", _C + ".events.owned"}


def _parse_dt(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ToolError(f"'{field}' must be ISO 8601, e.g. 2026-12-01T14:30")
    return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)


def _events(start: datetime, end: datetime, action: str) -> list[dict]:
    cal = google_service("calendar", "v3", READ_SCOPES, action)
    result = run(cal.events().list(
        calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(),
        singleEvents=True, orderBy="startTime", timeZone=TZ_NAME, maxResults=250,
    ), action)
    return result.get("items", [])


def _is_busy(event: dict) -> bool:
    if "dateTime" not in event.get("start", {}) or event.get("transparency") == "transparent":
        return False  # all-day or marked "free"
    for person in event.get("attendees", []):
        if person.get("self") and person.get("responseStatus") == "declined":
            return False
    return True


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def list_events(days_ahead: int = 7) -> list[dict]:
        """List events on the primary Google Calendar from now until days_ahead days
        from now (Asia/Jerusalem time)."""
        days_ahead = max(1, min(int(days_ahead), 365))
        now = datetime.now(TZ)
        return [{
            "id": e.get("id"),
            "title": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
            "location": e.get("location", ""),
        } for e in _events(now, now + timedelta(days=days_ahead), "list calendar events")]

    @mcp.tool()
    def find_free_slots(date: str, duration_minutes: int = 30) -> dict:
        """Find free time slots of at least duration_minutes on a date (YYYY-MM-DD),
        between 09:00 and 18:00 Asia/Jerusalem time."""
        try:
            day = Date.fromisoformat(date)
        except ValueError:
            raise ToolError("'date' must be in the form YYYY-MM-DD.")
        if duration_minutes <= 0:
            raise ToolError("'duration_minutes' must be a positive number.")
        need = timedelta(minutes=duration_minutes)
        day_start = datetime.combine(day, WORK_START, TZ)
        day_end = datetime.combine(day, WORK_END, TZ)
        busy = sorted(
            (_parse_dt(e["start"]["dateTime"], "start"), _parse_dt(e["end"]["dateTime"], "end"))
            for e in _events(day_start, day_end, "check free time") if _is_busy(e)
        )
        slots, cursor = [], day_start
        for b_start, b_end in busy:
            if b_start - cursor >= need:
                slots.append((cursor, b_start))
            cursor = max(cursor, b_end)
        if day_end - cursor >= need:
            slots.append((cursor, day_end))
        return {
            "date": date,
            "time_zone": TZ_NAME,
            "working_hours": f"{WORK_START:%H:%M}-{WORK_END:%H:%M}",
            "free_slots": [{"start": s.isoformat(), "end": e.isoformat()} for s, e in slots],
        }

    @mcp.tool()
    def create_event(title: str, start: str, end: str, description: str = "") -> dict:
        """Create an event on the primary Google Calendar. start and end are ISO 8601
        (e.g. 2026-12-01T14:30); times without an offset are Asia/Jerusalem time."""
        start_dt, end_dt = _parse_dt(start, "start"), _parse_dt(end, "end")
        if end_dt <= start_dt:
            raise ToolError("'end' must be after 'start'.")
        cal = google_service("calendar", "v3", WRITE_SCOPES, "create a calendar event")
        event = run(cal.events().insert(calendarId="primary", sendUpdates="none", body={
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": TZ_NAME},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": TZ_NAME},
        }), "create a calendar event")
        return {
            "id": event.get("id"),
            "title": event.get("summary"),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "link": event.get("htmlLink"),
        }
