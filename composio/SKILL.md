---
name: composio
version: 1.1.0
description: "Universal tool gateway via Composio — connect to 1000+ external apps (Gmail, Slack, GitHub, Google Calendar, Notion, etc.) through the Composio Gateway. Use when the user wants to interact with external SaaS services, send emails, manage calendars, access documents, or any third-party app integration."

metadata:
  starchild:
    emoji: "🔌"
    skillKey: composio

user-invocable: true
---

# Composio — External App Integration via Gateway

Composio lets users connect 1000+ external apps (Gmail, Slack, GitHub, Google Calendar, Notion, etc.) to their Starchild agent. All operations go through the **Composio Gateway** (`composio-gateway.fly.dev`), which handles auth and API key management.

## Architecture

```
Agent (Fly 6PN network)
    ↓  HTTP (auto-authenticated by IPv6)
Composio Gateway (composio-gateway.fly.dev)
    ↓  Composio SDK
Composio Cloud → Target API (Gmail, Slack, etc.)
```

- **You never touch the COMPOSIO_API_KEY** — the gateway holds it
- **You never call Composio SDK directly** — use the gateway HTTP API
- **Authentication is automatic** — your Fly 6PN IPv6 resolves to a user_id via the billing DB
- **No env vars needed** — the gateway is always accessible from any agent container

## Gateway Base URL

```
GATEWAY = "http://composio-gateway.flycast"
```

All requests use **plain HTTP over Fly internal network** (flycast). No JWT needed.

## API Reference

### 1. Search Tools (compact)

Find the right tool slug for a task. Returns **compact** tool info — just slug, description, and parameter names. Enough to pick the right tool.

```bash
curl -s -X POST $GATEWAY/internal/search \
  -H "Content-Type: application/json" \
  -d '{"query": "send email via gmail"}'
```

**Response (compact):**
```json
{
  "results": [{"primary_tool_slugs": ["GMAIL_SEND_EMAIL"], "use_case": "send email", ...}],
  "tool_schemas": {
    "GMAIL_SEND_EMAIL": {
      "tool_slug": "GMAIL_SEND_EMAIL",
      "toolkit": "gmail",
      "description": "Send an email...",
      "parameters": ["to", "subject", "body", "cc", "bcc"],
      "required": ["to", "subject", "body"]
    }
  },
  "toolkit_connection_statuses": [...]
}
```

### 2. Get Tool Schema (full)

Get the **complete** parameter definitions for a specific tool — types, descriptions, enums, defaults. Use this **after** search when you need exact parameter formats.

```bash
curl -s -X POST $GATEWAY/internal/tool_schema \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLECALENDAR_EVENTS_LIST"}'
```

**Response:**
```json
{
  "data": {
    "tool_slug": "GOOGLECALENDAR_EVENTS_LIST",
    "description": "Returns events on the specified calendar.",
    "input_parameters": {
      "properties": {
        "timeMin": {"type": "string", "description": "RFC3339 timestamp..."},
        "timeMax": {"type": "string", "description": "RFC3339 timestamp..."},
        "calendarId": {"type": "string", "default": "primary"}
      },
      "required": ["calendarId"]
    }
  },
  "error": null
}
```

### 3. Execute a Tool

Execute a Composio tool. **Key name is `arguments`, not `params`.**

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GMAIL_SEND_EMAIL", "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hello!"}}'
```

**On success:**
```json
{"data": {"messages": [...]}, "error": null}
```

**On failure** — includes tool_schema so you can self-correct:
```json
{
  "data": null,
  "error": "Missing required parameter: calendarId",
  "tool_schema": {
    "tool_slug": "GOOGLECALENDAR_EVENTS_LIST",
    "description": "...",
    "input_parameters": {"properties": {...}, "required": [...]}
  }
}
```

### 4. List User's Connections

```bash
curl -s $GATEWAY/internal/connections
```

### 5. Initiate New Connection

```bash
curl -s -X POST $GATEWAY/api/connect \
  -H "Content-Type: application/json" \
  -d '{"toolkit": "gmail"}'
```

Returns `connect_url` for the user to complete OAuth.

### 6. Disconnect

```bash
curl -s -X DELETE $GATEWAY/api/connections/{connection_id}
```

## Optimal Workflow (minimize tool calls)

### Known tool → Direct execute (1 call)

If you already know the tool slug and parameters from previous use or the Common Tools table below, **skip search entirely**:

```bash
curl -s -X POST $GATEWAY/internal/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "GOOGLECALENDAR_EVENTS_LIST", "arguments": {"calendarId": "primary", "timeMin": "2026-04-02T00:00:00+08:00", "timeMax": "2026-04-09T00:00:00+08:00", "singleEvents": true, "timeZone": "Asia/Hong_Kong"}}'
```

### Unknown tool → Search + Schema + Execute (2-3 calls)

1. **Search** (compact) → pick the right tool slug
2. **Get schema** (if param details unclear) → know exact argument format
3. **Execute** → with correct arguments

If execute fails, the error response **includes the full schema** — so you can retry immediately without an extra schema call.

### Wrap in a script for repeat use

For recurring queries, write a one-shot Python script:

```python
#!/usr/bin/env python3
import sys, json, requests
from datetime import datetime, timedelta, timezone

GATEWAY = "http://composio-gateway.flycast"
days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
tz_name = sys.argv[2] if len(sys.argv) > 2 else "UTC"

# ... build timeMin/timeMax ...
resp = requests.post(f"{GATEWAY}/internal/execute", json={
    "tool": "GOOGLECALENDAR_EVENTS_LIST",
    "arguments": {"calendarId": "primary", "timeMin": t_min, "timeMax": t_max,
                   "singleEvents": True, "timeZone": tz_name}
}).json()

# ... format and print ...
```

Then future calls are just: `bash("python3 scripts/calendar_events.py 7 Asia/Hong_Kong")` — **1 tool call**.

## Common Tools (skip search for these)

| App | Tool Slug | Key Arguments |
|-----|-----------|---------------|
| Gmail | `GMAIL_SEND_EMAIL` | `to`, `subject`, `body`, `cc`, `bcc` |
| Gmail | `GMAIL_FETCH_EMAILS` | `max_results`, `label_ids`, `q` (search query) |
| Google Calendar | `GOOGLECALENDAR_EVENTS_LIST` | `calendarId` (default: "primary"), `timeMin`, `timeMax` (RFC3339+tz), `singleEvents` (true), `timeZone` |
| Google Calendar | `GOOGLECALENDAR_CREATE_EVENT` | `calendarId`, `summary`, `start`, `end`, `description`, `attendees` |
| GitHub | `GITHUB_CREATE_ISSUE` | `owner`, `repo`, `title`, `body` |
| Slack | `SLACK_SEND_MESSAGE` | `channel`, `text` |
| Notion | `NOTION_CREATE_PAGE` | `parent_id`, `title`, `content` |

## Important Notes

- **Tool slugs** are UPPERCASE: `GMAIL_SEND_EMAIL`
- **Toolkit slugs** are lowercase: `gmail`, `github`
- **Arguments key**: always use `"arguments"`, never `"params"` — `params` silently gets ignored
- **Time parameters**: use RFC3339 with timezone offset (`2026-04-08T00:00:00+08:00`), not UTC unless intended
- **OAuth tokens are managed by Composio** — auto-refreshed on expiry
