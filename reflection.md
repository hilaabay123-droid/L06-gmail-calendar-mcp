# Reflection – L06: gmail-calendar MCP server

## What did we ask the agent?
I asked Claude Code to build an MCP server in Python called
"gmail-calendar". It uses last week's Google client and token, which
stay in my private folder (C:\privet-google-client) and are never
copied into the project. I asked for six tools: search_emails,
read_email, create_draft, list_events, find_free_slots and
create_event – and no tool that sends or deletes anything.
Then I asked the agent to test the server, register it in Claude Code,
write a PRD and save everything in Git without secrets. After that I
talked to it in free language: what is in my calendar tomorrow,
create a draft and an event 4 hours from now, and find a free hour
for a "Study group".

## How did we check that the result is correct?
- A test script (test_server.py) showed the 6 tools and read real
  events from my calendar.
- /mcp showed the server as connected with 6 tools.
- I opened Gmail and saw the "L06 test" draft, not sent. I opened
  Google Calendar and saw "MCP works" 4 hours after my request, and
  "Study group" in a free hour the next morning.
- I worked in manual mode, so the agent asked for my approval before
  each action, and I read the requests before approving.
- Before the commit, I checked that no token or client file was
  going into Git.

One thing surprised me: the first draft was addressed to a different
email address than the Gmail account I connected. The agent took it
from my Claude account. This showed me that the agent has access to
more information than I expected. So I need to be careful, not give
it permission for everything, and follow what it does – not only
check that it "worked".

## Which tool did we leave out, and why?
We left out any tool that sends emails or deletes emails or events.
When I asked the agent to send the draft and delete the event, it
said it has no tool for that and told me to do it myself.
This made me feel safer, because there is still a human in the loop
and I keep control over the important actions. In my work or studies
I would not give an agent permissions that can put me or my work at
risk. Sending and deleting are dangerous: mistakes cannot be undone,
and they open more room for cyber attacks – for example, an email
with hidden instructions that tries to make the agent forward my mail.

## L05 vs L06: what changed?
| | L05 (program + API) | L06 (MCP server) |
|---|---|---|
| How I run it | A fixed command: uv run google-test | A request in free language |
| Who decides the steps | The code | The model, from the server's tool list |
| A new request | Needs a new prompt and a new program | Same server, no new code |
| Checking the calendar | Not possible | find_free_slots |

The biggest difference for me is the freedom and how easy it is to
use. In L05 the program could do only one thing. In L06 I asked for
something new ("find a free hour and add Study group") and it worked
without any new code.

What is still not clear to me: I don't yet fully understand every
step the agent did behind the scenes. I would like to get a deeper
explanation of what we are building in the course and why it matters.

---
*AI use: I wrote my answers in Hebrew, and Claude translated them into
English and helped me phrase and organize the reflection.*
