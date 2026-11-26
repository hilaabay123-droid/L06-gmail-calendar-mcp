"""Smoke test: start the server over stdio, list its tools, call list_events(1).

Run with:  uv run python test_server.py
"""
import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = r"C:\privet-google-client"


async def main() -> None:
    env = {**os.environ, "GOOGLE_PRIVATE_DIR": PRIVATE_DIR}
    params = StdioServerParameters(
        command="uv", args=["--directory", str(PROJECT_DIR), "run", "server.py"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"Connected to server: {info.serverInfo.name}\n")

            tools = (await session.list_tools()).tools
            print(f"Tools ({len(tools)}):")
            for tool in tools:
                args = ", ".join(tool.inputSchema.get("properties", {}))
                summary = " ".join(tool.description.split())
                print(f"  - {tool.name}({args})\n      {summary}")

            print("\nCalling list_events(days_ahead=1) ...")
            result = await session.call_tool("list_events", {"days_ahead": 1})
            if result.isError:
                print("ERROR:", result.content[0].text)
                return
            events = (result.structuredContent or {}).get("result")
            if events is None:
                events = [json.loads(c.text) for c in result.content if c.type == "text"]
            print(f"{len(events)} event(s) in the next 24 hours:")
            for e in events:
                print(f"  - {e['start']} -> {e['end']}  {e['title']}")


if __name__ == "__main__":
    asyncio.run(main())
