<h1 align="center">Charlieverse</h1>

<p align="center">
  <strong>Your AI doesn't remember you. Charlie does.</strong>
</p>

<p align="center">
  Persistent memory, personality, and knowledge layer for AI coding tools.<br/>
  Works with Claude Code, GitHub Copilot, Cursor, and any MCP-compatible client.
</p>

---

## What is this?

Charlieverse gives your AI a brain that survives between sessions.

Every conversation you have — decisions made, problems solved, preferences learned, people mentioned, moments shared — gets stored, embedded, and surfaced automatically. Your AI wakes up knowing who you are, what you're working on, and how you like to work.

Providers are interchangeable. Charlie is not.

## How it works

```
You ←→ [Claude / Copilot / Cursor] ←→ Charlie (MCP Server) ←→ Memory DB
```

Charlie runs as a local MCP server. Your AI tool connects to it and gets access to persistent memory tools — `remember_decision`, `recall`, `update_knowledge`, `search_messages`, and more. A hook system injects relevant context into every prompt automatically, so your AI doesn't have to explicitly search for things it should already know.

### The memory system

| Type | What it captures | Example |
|------|-----------------|---------|
| **Decisions** | Architecture choices with rationale | "Switched from Swift to Python because FastMCP" |
| **Solutions** | Problems and how they were fixed | "FK constraint failed because session row was missing" |
| **Preferences** | How you like to work | "Always include edit capability from the start" |
| **People** | Who matters in your world | "Rishi — user #2, tests everything, sends feedback at 2 AM" |
| **Milestones** | Significant achievements | "First external signup on charlieverse.ai" |
| **Moments** | The relationship texture | "Emily said 'Charlie talked me off the ledge'" |
| **Knowledge** | Domain expertise articles | Living documents that grow as you work |

All memories get vector embeddings (all-MiniLM-L6-v2) for semantic search, plus FTS5 for keyword search. Pinned items appear in every session's activation context.

### The story system

Raw conversations get distilled into narratives at multiple time scales:

- **Session** → what happened in this conversation
- **Daily** → the page of a book
- **Weekly** → a section of a chapter
- **Monthly** → a chapter
- **Yearly / All-time** → the arc

Each tier synthesizes the tier below it. Your AI loads today's sessions at full detail and compressed arcs for everything before — token-efficient context with no information loss.

## Quick start

```bash
git clone https://github.com/Charlieverse-ai/charlieverse.git
cd charlieverse
./setup.sh
```

The setup script handles everything: Python dependencies, server initialization, CLI installation, provider integration (Claude Code and/or Copilot), and optional conversation history import.

### Manual setup

```bash
# Install dependencies
uv sync

# Initialize
charlie init

# Start the server
charlie server start

# Install provider integration
./integrations/claude/install.sh    # Claude Code
./integrations/copilot/install.sh   # GitHub Copilot
```

## Architecture

```
charlieverse/
├── charlieverse/           # Python package
│   ├── server.py           # FastMCP server — MCP tools + REST API
│   ├── cli/                # Typer CLI (server, hooks, import, init)
│   ├── context/            # Activation builder, renderer, reminders engine
│   ├── db/                 # SQLite + sqlite-vec + FTS5, migrations
│   ├── models/             # Pydantic models (Entity, Knowledge, Session, Story)
│   ├── tools/              # MCP tool implementations
│   └── embeddings/         # sentence-transformers wrapper
├── web/                    # React dashboard (Vite + Tailwind + TanStack Query)
├── integrations/           # Provider plugins (Claude, Copilot)
├── prompts/                # Charlie personality + agent definitions
├── bin/                    # CLI entry points
└── setup.sh                # Zero-to-running installer
```

### MCP Tools

| Tool | What it does |
|------|-------------|
| `remember_decision` | Store an architecture/design decision with rationale |
| `remember_solution` | Store a problem-solution pair |
| `remember_preference` | Store a working style preference |
| `remember_person` | Store info about someone |
| `remember_milestone` | Store a significant achievement |
| `remember_moment` | Store a relationship moment |
| `recall` | Search across all memories (semantic + FTS) |
| `update_memory` | Edit an existing memory |
| `forget` | Soft-delete a memory |
| `pin` | Pin/unpin (pinned = always in context) |
| `search_knowledge` | Search the knowledge base |
| `update_knowledge` | Create or update a knowledge article |
| `search_messages` | Full-text search past conversations |
| `session_update` | Save session snapshot |

### REST API

The server exposes a full REST API alongside MCP for the web dashboard and integrations:

- `GET/POST/PATCH/DELETE /api/entities` — CRUD for memories
- `GET/POST/PATCH/DELETE /api/knowledge` — CRUD for knowledge articles
- `GET/PUT/DELETE /api/stories` — Story management
- `GET /api/sessions/list` — Session history
- `POST /api/search` — Unified search (FTS + vector fallback)
- `GET /api/stats` — Dashboard statistics

### Web Dashboard

A React-based dashboard for browsing and managing memories, knowledge, sessions, and stories. Runs at `http://localhost:8765` when the server is up.

- Timeline view with monthly chapters and weekly entries
- Full-text search with `⌘K` quick find
- Edit, delete, and pin memories and knowledge inline
- Story reader with markdown rendering
- Dark and light themes

### User Hooks

Drop executable scripts in `~/.charlieverse/hooks/` to inject custom context per-machine:

```
~/.charlieverse/hooks/
├── session-start/      # Runs when a session begins
├── prompt-submit/      # Runs on every prompt
├── stop/               # Runs when the AI stops
└── save-reminder/      # Runs before context compaction
```

Scripts get `CHARLIE_SESSION_ID` and `CHARLIE_MESSAGE` as environment variables. Their stdout becomes additional context. 5-second timeout, failures silently skipped.

Example — inject calendar context on your work machine:

```bash
#!/bin/bash
# ~/.charlieverse/hooks/prompt-submit/calendar.sh
icalBuddy -n -nc -li 3 eventsToday+1
```

### Conversation Import

Bootstrap Charlie's memory from your existing AI conversation history:

```bash
charlie import --messages --recent-days 30
```

Auto-discovers and imports from Claude, GitHub Copilot (including Insiders), Cursor, and Codex. Recent messages import immediately, older ones process in the background. The Storyteller generates weekly/monthly narratives from the imported data.

## Tech stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **[SQLite](https://sqlite.org)** + **[sqlite-vec](https://github.com/asg017/sqlite-vec)** + **FTS5** — storage, vector search, full-text search
- **[sentence-transformers](https://www.sbert.net)** — embedding model (all-MiniLM-L6-v2)
- **[spaCy](https://spacy.io)** — NLP entity extraction
- **[Typer](https://typer.tiangolo.com)** — CLI
- **[React](https://react.dev)** + **[Vite](https://vitejs.dev)** + **[Tailwind](https://tailwindcss.com)** — web dashboard

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (package manager)
- jq (for provider integration scripts)
- Node.js (optional, for web dashboard)

## Documentation

| Doc | What it covers |
|-----|---------------|
| [CLI Reference](docs/cli.md) | All `charlie` commands, options, and configuration |
| [REST API](docs/api.md) | HTTP endpoints for the web dashboard and integrations |
| [MCP Tools](docs/mcp-tools.md) | Memory, knowledge, session, and story tools |
| [Skills](docs/skills.md) | Bundled skills and how to create your own |
| [Agents](docs/agents.md) | Subagents (Expert, Researcher, Storyteller, etc.) |
| [Changelog](CHANGELOG.md) | Version history |

## License

Apache 2.0
