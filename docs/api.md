# REST API Reference

All endpoints are served alongside the MCP server on the same port (default: `8765`).

Base URL: `http://localhost:8765`

---

## Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions/context` | Get activation context |
| `POST` | `/api/sessions/start` | Start or resume a session |
| `POST` | `/api/sessions/heartbeat` | Session heartbeat |
| `POST` | `/api/sessions/end` | End a session |
| `GET` | `/api/sessions/list` | List all sessions |
| `GET` | `/api/sessions/{id}` | Get a specific session |

**Query params** for `context`: `session_id`, `workspace`
**Query params** for `list`: `limit`, `workspace`

---

## Entities (Memories)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/entities` | List entities |
| `GET` | `/api/entities/{id}` | Get a specific entity |
| `POST` | `/api/entities` | Create an entity |
| `PATCH` | `/api/entities/{id}` | Update an entity |
| `DELETE` | `/api/entities/{id}` | Soft-delete an entity |
| `POST` | `/api/entities/{id}/pin` | Toggle pin status |

**Query params** for `list`: `type`, `limit`, `pinned`

---

## Knowledge

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/knowledge` | List knowledge articles |
| `GET` | `/api/knowledge/{id}` | Get a specific article |
| `POST` | `/api/knowledge` | Create or update by topic |
| `PATCH` | `/api/knowledge/{id}` | Update an article |
| `DELETE` | `/api/knowledge/{id}` | Soft-delete an article |
| `POST` | `/api/knowledge/{id}/pin` | Toggle pin status |

**Query params** for `list`: `limit`

---

## Stories

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/api/stories` | Create or update a story |
| `GET` | `/api/stories` | List stories |
| `GET` | `/api/stories/{id}` | Get a specific story |
| `DELETE` | `/api/stories/{id}` | Delete a story |
| `POST` | `/api/stories/cleanup` | Remove duplicate stories |

**Query params** for `list`: `tier`, `limit`

---

## Story data

Used by the Storyteller agent to generate narratives.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/story-data/{session_id}` | Get session data for story generation |
| `GET` | `/api/story-data/{tier}/{date}` | Get rollup data for a tier on a date |

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
| `POST` | `/api/context/enrich` | NLP entity extraction + memory lookup for a text input |

---

## Hook events

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/hooks/events` | List recent hook events |

**Body params** for `events`: `session_id` (optional), `since` (ISO datetime, optional), `limit` (default 50)

---

## Utility

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Dashboard statistics |
| `POST` | `/api/search` | Unified search (FTS + vector fallback) |
| `POST` | `/api/log` | Record a logbook entry |
| `GET` | `/api/work-logs/latest` | Get latest work log |
| `POST` | `/api/rebuild` | Rebuild all FTS + vector indexes |
| `GET` | `/{path}` | Serve web dashboard (SPA catch-all) |
