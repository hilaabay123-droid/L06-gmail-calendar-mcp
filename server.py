"""gmail-calendar MCP server (stdio).

Tools: search_emails, read_email, create_draft, list_events, find_free_slots,
create_event. There is deliberately no tool that sends or deletes anything.
Never write to stdout here: stdout carries the MCP protocol.
"""
from mcp.server.fastmcp import FastMCP

import calendar_tools
import gmail_tools

mcp = FastMCP("gmail-calendar")
gmail_tools.register(mcp)
calendar_tools.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
