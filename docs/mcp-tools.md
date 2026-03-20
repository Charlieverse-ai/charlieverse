# MCP Tools Reference

These tools are available to any MCP-compatible client connected to the Charlieverse server.

## Memory Tools

### remember_decision
Store a decision and why it was made.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `decision` | string | yes | The decision |
| `rationale` | string | no | Why this decision was made |
| `tags` | string[] | no | Tags for categorization |
| `pinned` | bool | no | Pin to always appear in context |

### remember_solution
Store a problem and how it was solved.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `problem` | string | yes | The problem |
| `solution` | string | yes | How it was solved |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

### remember_preference
Store a working style preference.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | string | yes | The preference |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

### remember_person
Store info about a person.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | string | yes | Who they are, relationship, context |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

### remember_milestone
Store a significant achievement.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `milestone` | string | yes | The achievement |
| `significance` | string | no | Why it matters |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

### remember_moment
Store a relationship moment (journal-style).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `moment` | string | yes | What happened |
| `feeling` | string | no | How it felt |
| `context` | string | no | Background context |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

### recall
Search across all memories, knowledge, and messages.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `type` | string | no | Filter by entity type |
| `limit` | int | no | Max results (default: 10) |

### update_memory
Edit an existing memory's content and/or tags.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory ID |
| `content` | string | no | New content |
| `tags` | string[] | no | New tags |

### forget
Soft-delete a memory.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory ID |

### pin
Pin or unpin a memory (pinned = always in activation context).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Memory ID |
| `pinned` | bool | yes | Pin state |

## Knowledge Tools

### search_knowledge
Search the knowledge base.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `limit` | int | no | Max results (default: 5) |

### update_knowledge
Create or update a knowledge article.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | yes | Article topic (used as key for upsert) |
| `content` | string | yes | Article content |
| `tags` | string[] | no | Tags |
| `pinned` | bool | no | Pin to context |

## Message Tools

### search_messages
Full-text search past conversation messages.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `limit` | int | no | Max results (default: 20) |

## Session Tools

### session_update
Save a session snapshot.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `what_happened` | string | yes | Summary of the session |
| `for_next_session` | string | yes | What to pick up next time |
| `tags` | string[] | no | Tags |
| `workspace` | string | no | Workspace path |

## Story Tools

### upsert_story
Create or update a story.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | yes | Story title |
| `content` | string | yes | Story content |
| `tier` | string | yes | Tier: session, daily, weekly, monthly, yearly, all-time |
| `period_start` | string | yes | ISO date |
| `period_end` | string | yes | ISO date |
| `summary` | string | no | Short summary |
| `tags` | string[] | no | Tags |

### list_stories
List stories, optionally filtered by tier.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tier` | string | no | Filter by tier |
| `limit` | int | no | Max results (default: 20) |

### get_story
Get a story by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Story ID |

### delete_story
Delete a story.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | yes | Story ID |

### get_story_data
Get data for generating stories.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target` | string | yes | Session ID or tier name (daily, weekly, monthly) |
