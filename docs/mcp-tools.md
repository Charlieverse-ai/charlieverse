# MCP Tools Reference

These tools are available to any MCP-compatible client connected to the Charlieverse server.

---

## Memory tools

### `save_memory`

Record anything Charlie learns about the human and their world. A single tool for all memory types — pick the type by how the memory will be used.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | EntityType | yes | `decision`, `solution`, `preference`, `person`, `milestone`, `moment`, `project`, or `event` |
| `content` | string | yes | The memory content — specific, self-contained |
| `session_id` | string | yes | Session to associate with |
| `tags` | string[] | yes | Tags for categorization |
| `pinned` | bool | yes | Pin to always appear in context |

Memory type meanings:
- `decision` — a choice made and why, so we don't relitigate it
- `solution` — a problem solved and how, so we don't re-solve it
- `preference` — how they want things, so Charlie doesn't have to be told twice
- `person` — who they are, what they've been through, how the human sees them
- `milestone` — something shipped or a threshold crossed
- `moment` — something that shaped the work or the relationship emotionally
- `project` — something in flight — the shape of it, what it's for, where it stands
- `event` — something that happened at a specific time

Before creating a new memory, check the activation context and recent recalls for one that already covers the subject — prefer `update_memory` over creating duplicates.

### `update_memory`

Refine an existing memory when Charlie learns something new about the same thing. Preserves creation date and provenance.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory ID |
| `session_id` | string | yes | Session context for the update |
| `content` | string | yes | New content (replaces the old — carry forward what's still true) |
| `tags` | string[] | yes | New tags (replaces the old) |

### `forget_memory`

Soft-delete a memory.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory ID |

### `pin`

Pin or unpin an entity or knowledge article. Pinned items always appear in activation context.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory or knowledge article ID |
| `pinned` | bool | yes | Pin state |

---

## Search

### `search_memories`

Search across entities, knowledge, stories, and messages. Results are relevance-ordered using a combination of FTS, semantic similarity, and recency.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `limit` | int | no | Max results (default: 10) |

### `search_conversations`

Full-text search past conversation messages.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `limit` | int | no | Max results (default: 20) |
| `session_id` | string | no | Limit to a specific session |

---

## Knowledge tools

### `update_article`

Create or update a knowledge article. Upserts on topic.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | yes | Article topic (used as key for upsert) |
| `content` | string | yes | Article content |
| `session_id` | string | yes | Session to associate with |
| `tags` | string[] | yes | Tags |
| `pinned` | bool | no | Pin to context |

---

## Session tools

### `activation_context`

Build and return the rendered activation context for a session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace` | string | yes | Workspace path |
| `session_id` | string | yes | Session ID |

### `update_session`

Update the session with the provided fields. Omit a field to keep the existing value.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | Session ID |
| `workspace` | string | yes | Workspace path |
| `content` | object | no | `{ what_happened, for_next_session }` |
| `tags` | string[] | no | Tags |

---

## Story tools

### `save_story`

Create or update a story. For session stories, matches on `session_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | yes | Story title |
| `content` | string | yes | Story content |
| `tier` | string | yes | `session`, `daily`, `weekly`, `monthly`, `yearly`, or `all-time` |
| `period_start` | date | yes | ISO date |
| `period_end` | date | yes | ISO date |
| `summary` | string | yes | Short summary |
| `session_id` | string | yes | Session to associate with (used for upsert matching) |
| `workspace` | string | yes | Workspace path |
| `tags` | string[] | yes | Tags |

### `forget_story`

Delete a story.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Story ID |
