"""Read-only test of the gmail-calendar server against the real Google account.

Starts the server over stdio, lists its tools, then calls only read-only tools:
list_events(1), find_free_slots(tomorrow, 60), search_emails("L06 test", 1) and
read_email on that result. It never creates, sends or deletes anything, and it
prints no email addresses or message text (subjects only).

Run with:  uv run python test_server.py
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = os.environ.get("GOOGLE_PRIVATE_DIR", r"C:\privet-google-client")
READ_ONLY = {"list_events", "find_free_slots", "search_emails", "read_email"}
FORBIDDEN_WORDS = ("send", "delete", "trash", "remove")


async def call(session: ClientSession, name: str, args: dict, returns_list: bool):
    """Call a read-only tool and return its parsed result (or raise on error)."""
    assert name in READ_ONLY, f"{name} is not a read-only tool"
    shown = {k: ("<id hidden>" if k == "message_id" else repr(v)) for k, v in args.items()}
    print(f"\n{name}({', '.join(f'{k}={v}' for k, v in shown.items())})")
    result = await session.call_tool(name, args)
    if result.isError:
        raise RuntimeError(result.content[0].text)
    data = result.structuredContent
    if isinstance(data, dict) and returns_list:
        return data.get("result", [])
    if data is not None:
        return data
    items = [json.loads(c.text) for c in result.content if c.type == "text"]
    return items if returns_list else items[0]


async def main() -> None:
    env = {**os.environ, "GOOGLE_PRIVATE_DIR": PRIVATE_DIR}
    params = StdioServerParameters(
        command="uv", args=["--directory", str(PROJECT_DIR), "run", "server.py"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"Connected to server: {info.serverInfo.name}")

            tools = (await session.list_tools()).tools
            print(f"\nTools ({len(tools)}):")
            for tool in tools:
                print(f"  - {tool.name}({', '.join(tool.inputSchema.get('properties', {}))})")
            bad = [t.name for t in tools if any(w in t.name for w in FORBIDDEN_WORDS)]
            print("No send/delete tools: " + ("OK" if not bad else f"FAIL {bad}"))

            events = await call(session, "list_events", {"days_ahead": 1}, returns_list=True)
            print(f"  {len(events)} event(s) in the next 24 hours")
            for e in events:
                print(f"    {e['start']} -> {e['end']}  {e['title']}")

            tomorrow = (datetime.now(ZoneInfo("Asia/Jerusalem")) + timedelta(days=1)).date()
            slots = await call(session, "find_free_slots",
                               {"date": tomorrow.isoformat(), "duration_minutes": 60},
                               returns_list=False)
            print(f"  working hours {slots['working_hours']}, {len(slots['free_slots'])} free slot(s)")
            for s in slots["free_slots"]:
                print(f"    {s['start']} -> {s['end']}")

            found = await call(session, "search_emails", {"query": "L06 test", "max_results": 1},
                               returns_list=True)
            print(f"  {len(found)} message(s) found")
            if not found:
                print("  Nothing to read; read_email skipped.")
                return
            print(f"    subject: {found[0]['subject']}")

            msg = await call(session, "read_email", {"message_id": found[0]["id"]},
                             returns_list=False)
            print(f"  subject: {msg['subject']}")
            print(f"  date: {msg['date']}")
            print(f"  labels: {', '.join(msg['labels'])}")
            print(f"  body: {len(msg['body'])} characters (not shown)")

            print("\nAll read-only tools worked. Nothing was created, sent or deleted.")


if __name__ == "__main__":
    asyncio.run(main())
