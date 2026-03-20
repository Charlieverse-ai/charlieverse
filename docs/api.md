# REST API Reference

All endpoints are served alongside the MCP server on the same port (default: 8765).

## Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sessions/context` | Get activation context. Params: `session_id`, `workspace` |
| POST | `/api/sessions/start` | Start or resume a session |
| POST | `/api/sessions/heartbeat` | Session heartbeat |
| POST | `/api/sessions/end` | End a session |
| GET | `/api/sessions/list` | List all sessions. Params: `limit`, `workspace` |
| GET | `/api/sessions/{id}` | Get a specific session |

## Entities (Memories)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/entities` | List entities. Params: `type`, `limit`, `pinned` |
| GET | `/api/entities/{id}` | Get a specific entity |
| POST | `/api/entities` | Create an entity |
| PATCH | `/api/entities/{id}` | Update an entity |
| DELETE | `/api/entities/{id}` | Soft-delete an entity |
| POST | `/api/entities/{id}/pin` | Toggle pin status |

## Knowledge

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/knowledge` | List knowledge articles. Params: `limit` |
| GET | `/api/knowledge/{id}` | Get a specific article |
| POST | `/api/knowledge` | Create or update by topic |
| PATCH | `/api/knowledge/{id}` | Update an article |
| DELETE | `/api/knowledge/{id}` | Soft-delete an article |
| POST | `/api/knowledge/{id}/pin` | Toggle pin status |

## Stories

| Method | Path | Description |
|--------|------|-------------|
| PUT | `/api/stories` | Create or update a story |
| GET | `/api/stories` | List stories. Params: `tier`, `limit` |
| GET | `/api/stories/{id}` | Get a specific story |
| DELETE | `/api/stories/{id}` | Delete a story |
| POST | `/api/stories/cleanup` | Remove duplicate stories |

## Story Data (for Storyteller)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/story-data/{session_id}` | Get session data for story generation |
| GET | `/api/story-data/{tier}/{date}` | Get rollup data for a tier on a date |

## Messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/messages` | Store a message |
| GET | `/api/messages/latest` | Get latest message. Params: `session_id`, `role` |
| POST | `/api/messages/search` | Full-text search messages |

## Context

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/context/enrich` | NLP entity extraction + memory lookup for a text input |

## Other

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/search` | Unified search (FTS + vector fallback) |
| POST | `/api/log` | Record a logbook entry |
| GET | `/api/work-logs/latest` | Get latest work log |
| POST | `/api/rebuild` | Rebuild all FTS + vector indexes |
| GET | `/{path}` | Serve web dashboard (SPA catch-all) |
