# REST API Reference

All endpoints are served alongside the MCP server on the same port (default: `8765`).

Base URL: `http://localhost:8765`

---

## Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions/context` | Preview activation context as plain text |
| `POST` | `/api/sessions/start` | Start or resume a session; returns rendered activation context |
| `POST` | `/api/sessions/end` | End a session |
| `GET` | `/api/sessions/list` | List recent sessions |
| `GET` | `/api/sessions/{id}` | Get a specific session |
| `GET` | `/api/session/{session_id}/prompt_submit` | Timing data for the prompt-submit hook (session age, last save, seen memory IDs) |

**Query params** for `context`: `session_id`, `workspace`
**Query params** for `list`: `limit` (default 50)

---

## Memories

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memories` | List memories |
| `GET` | `/api/memories/{id}` | Get a specific memory |
| `POST` | `/api/memories` | Create a memory |
| `PATCH` | `/api/memories/{id}` | Update a memory |
| `DELETE` | `/api/memories/{id}` | Soft-delete a memory |
| `POST` | `/api/memories/{id}/pin` | Toggle pin status |

**Query params** for list: `type`, `limit` (default 100)

---

## Knowledge

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/knowledge` | List knowledge articles |
| `GET` | `/api/knowledge/{id}` | Get a specific article |
| `POST` | `/api/knowledge` | Create a knowledge article |
| `PATCH` | `/api/knowledge/{id}` | Update an article |
| `DELETE` | `/api/knowledge/{id}` | Soft-delete an article |
| `POST` | `/api/knowledge/{id}/pin` | Toggle pin status |

**Query params** for `list`: `limit` (default 50)

---

## Stories

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/api/stories` | Create or update a story |
| `GET` | `/api/stories` | List stories |
| `GET` | `/api/stories/{id}` | Get a specific story |
| `DELETE` | `/api/stories/{id}` | Delete a story |
| `POST` | `/api/stories/cleanup` | Delete stories with empty, short, or stub titles |

**Query params** for `list`:

- `tier` — filter by story tier (`session`, `daily`, `weekly`, `monthly`, `yearly`, `all-time`)
- `period_start` / `period_end` — inclusive date range (`YYYY-MM-DD`). When both are provided, stories whose period overlaps the range are returned via timezone-aware matching.
- `limit` — cap on results when no period range is specified (default 50)

---

## Story data

Used by the Storyteller agent to generate narratives.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/story-data/{tier}/{date}` | Get rollup data for a tier on a date |

Tier is one of `daily`, `weekly`, `monthly`, `yearly`, `all-time`. For `daily`, returns raw sessions, messages, memories, and knowledge created that day. For higher tiers, returns the lower-tier stories within the tier's period.

---

## Messages

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/messages` | Store a message |
| `GET` | `/api/messages/latest` | Get latest message |
| `POST` | `/api/messages/search` | Full-text search messages |

**Query params** for `latest`: `session_id`, `role`

---

## Context

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/context/enrich` | NLP entity extraction + memory/story lookup for a text input |

Used by the reminders engine on every prompt. Returns found memories grouped by extracted entity, plus temporally-relevant stories.

---

## Utility

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Dashboard statistics (entity counts by type, session count, knowledge count) |
| `POST` | `/api/search` | Unified search (FTS5 with vector fallback) across memories and knowledge |
| `GET` | `/{path}` | Serve web dashboard (SPA catch-all) |
