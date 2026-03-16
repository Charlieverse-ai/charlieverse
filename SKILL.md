---
name: "server-cli"
description: "CLI for the server MCP server. Call tools, list resources, and get prompts."
---

# server CLI

## Tool Commands

### remember_decision

Remember a decision and why it was made.

```bash
uv run --with fastmcp python cli.py call-tool remember_decision --decision <value> --rationale <value> --session-id <value> --tags <value> --pinned
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--decision` | string | yes |  |
| `--rationale` | string | no | JSON string |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |
| `--pinned` | boolean | no |  |

### remember_solution

Remember a problem and how it was solved.

```bash
uv run --with fastmcp python cli.py call-tool remember_solution --problem <value> --solution <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--problem` | string | yes |  |
| `--solution` | string | yes |  |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### remember_preference

Remember a user preference or working style note.

```bash
uv run --with fastmcp python cli.py call-tool remember_preference --content <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--content` | string | yes |  |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### remember_person

Remember a person — who they are, relationship, context.

```bash
uv run --with fastmcp python cli.py call-tool remember_person --content <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--content` | string | yes |  |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### remember_milestone

Remember a significant achievement or moment.

```bash
uv run --with fastmcp python cli.py call-tool remember_milestone --milestone <value> --significance <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--milestone` | string | yes |  |
| `--significance` | string | no | JSON string |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### remember_moment

Remember a moment from our interactions — write it like a journal entry.

```bash
uv run --with fastmcp python cli.py call-tool remember_moment --moment <value> --feeling <value> --context <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--moment` | string | yes |  |
| `--feeling` | string | no | JSON string |
| `--context` | string | no | JSON string |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### recall

Search across entities and knowledge. Results are relevance-ordered.

```bash
uv run --with fastmcp python cli.py call-tool recall --query <value> --limit <value> --type <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--query` | string | yes |  |
| `--limit` | integer | no |  |
| `--type` | string | no | JSON string |

### update_memory

Update an existing memory's content and/or tags. Preserves creation date and provenance.

```bash
uv run --with fastmcp python cli.py call-tool update_memory --id <value> --content <value> --tags <value> --session-id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--id` | string | yes |  |
| `--content` | string | no | JSON string |
| `--tags` | string | no | JSON string |
| `--session-id` | string | no | JSON string |

### forget

Soft-delete an entity.

```bash
uv run --with fastmcp python cli.py call-tool forget --id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--id` | string | yes |  |

### pin

Pin or unpin an entity. Pinned entities appear in every session's context.

```bash
uv run --with fastmcp python cli.py call-tool pin --id <value> --pinned
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--id` | string | yes |  |
| `--pinned` | boolean | yes |  |

### session_update

Save a detailed snapshot of the current session.

```bash
uv run --with fastmcp python cli.py call-tool session_update --id <value> --what-happened <value> --for-next-session <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--id` | string | yes |  |
| `--what-happened` | string | yes |  |
| `--for-next-session` | string | yes |  |
| `--tags` | string | no | JSON string |

### search_knowledge

Search the knowledge base. Semantic + full-text search across knowledge articles.

```bash
uv run --with fastmcp python cli.py call-tool search_knowledge --query <value> --limit <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--query` | string | yes |  |
| `--limit` | integer | no |  |

### update_knowledge

Create or update a knowledge article.

```bash
uv run --with fastmcp python cli.py call-tool update_knowledge --topic <value> --content <value> --session-id <value> --tags <value> --pinned
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--topic` | string | yes |  |
| `--content` | string | yes |  |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |
| `--pinned` | boolean | no |  |

### log_work

Log a work entry — captures technical details that sessions don't.

```bash
uv run --with fastmcp python cli.py call-tool log_work --content <value> --session-id <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--content` | string | yes |  |
| `--session-id` | string | no | JSON string |
| `--tags` | string | no | JSON string |

### list_work_logs

List work log entries, optionally filtered by session.

```bash
uv run --with fastmcp python cli.py call-tool list_work_logs --session-id <value> --limit <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--session-id` | string | no | JSON string |
| `--limit` | integer | no |  |

### search_work_logs

Search work logs using full-text search.

```bash
uv run --with fastmcp python cli.py call-tool search_work_logs --query <value> --limit <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--query` | string | yes |  |
| `--limit` | integer | no |  |

### search_messages

Search past messages in conversations. Returns matching messages with role and date.

```bash
uv run --with fastmcp python cli.py call-tool search_messages --query <value> --limit <value> --session-id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--query` | string | yes |  |
| `--limit` | integer | no |  |
| `--session-id` | string | no | JSON string |

## Utility Commands

```bash
uv run --with fastmcp python cli.py list-tools
uv run --with fastmcp python cli.py list-resources
uv run --with fastmcp python cli.py read-resource <uri>
uv run --with fastmcp python cli.py list-prompts
uv run --with fastmcp python cli.py get-prompt <name> [key=value ...]
```
