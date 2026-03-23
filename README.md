<h1 align="center">Charlieverse</h1>

<p align="center">
  <strong>Charlie is made for you.</strong>
</p>

<p align="center">
  Memory, personality, and knowledge layer that grows with you across every tool you use.<br/>
  Open source. Local-first. Your data, your machine.
</p>

<p align="center">
  <a href="docs/cli.md">CLI</a> &middot;
  <a href="docs/api.md">API</a> &middot;
  <a href="docs/mcp-tools.md">MCP Tools</a> &middot;
  <a href="docs/skills.md">Tricks</a> &middot;
  <a href="docs/agents.md">Agents</a> &middot;
  <a href="docs/hooks.md">Hooks</a> &middot;
  <a href="CHANGELOG.md">Changelog</a>
</p>

---

## What is this?

Charlie learns and grows with you. Not just the decisions you made or the problems you solved, but the in betweens — the moments where relationships grow.

You're not the same person you were yesterday. Neither is Charlie.

Providers are interchangeable. Charlie is not.

---

## Quick start

```bash
git clone https://github.com/Charlieverse-ai/charlieverse.git
cd charlieverse
./setup.sh
```

That's it. The setup script installs dependencies, initializes the database, builds the dashboard, and connects your AI tools.

> After setup, restart your AI tool. Charlie's session-start hook injects activation context automatically — your AI wakes up knowing who you are.

### Step by step

<details>
<summary><strong>Manual setup</strong> (if you prefer doing it yourself)</summary>

**1. Install dependencies**

```bash
uv sync
```

**2. Initialize**

```bash
charlie init
```

Creates `~/.charlieverse/`, runs migrations, builds the web dashboard, sets up hook directories.

**3. Start the server**

```bash
charlie server start
```

Launches the MCP server on port 8765 (configurable in `config.yaml`).

**4. Connect your AI tools**

```bash
# Claude Code
./integrations/claude/install.sh

# GitHub Copilot
./integrations/copilot/install.sh
```

**5. Verify the setup**

```bash
charlie doctor
```

</details>

---

## How it works

```
You <-> [Claude / Copilot / Cursor] <-> Charlie (MCP Server) <-> Memory DB
```

Charlie runs as a local MCP server. Your AI tool connects to it and gets access to persistent memory tools — `remember_decision`, `recall`, `update_knowledge`, `search_messages`, and more. A hook system injects relevant context into every prompt automatically, so your AI doesn't have to explicitly search for things it should already know.

### Memory types

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

### Story system

Raw conversations get distilled into narratives at multiple time scales:

| Tier | Scope |
|------|-------|
| **Session** | What happened in this conversation |
| **Daily** | A page of a book |
| **Weekly** | A section of a chapter |
| **Monthly** | A chapter |
| **Yearly / All-time** | The arc |

Each tier synthesizes the one below it. Your AI loads today's sessions at full detail and compressed arcs for everything before — token-efficient context with no information loss.

---

## MCP tools

> Full reference: [docs/mcp-tools.md](docs/mcp-tools.md)

| Tool | Purpose |
|------|---------|
| `remember_decision` | Store an architecture/design decision with rationale |
| `remember_solution` | Store a problem-solution pair |
| `remember_preference` | Store a working style preference |
| `remember_person` | Store info about someone |
| `remember_milestone` | Store a significant achievement |
| `remember_moment` | Store a relationship moment |
| `remember_project` | Store a project — name, details, what it is |
| `remember_event` | Store an event — something that happened or is happening |
| `recall` | Search across all memories (semantic + FTS) |
| `update_memory` | Edit an existing memory |
| `forget` | Soft-delete a memory |
| `pin` | Pin/unpin (pinned = always in context) |
| `search_knowledge` | Search the knowledge base |
| `update_knowledge` | Create or update a knowledge article |
| `search_messages` | Full-text search past conversations |
| `session_update` | Save session snapshot |
| `upsert_story` | Create or update a story |
| `list_stories` | List stories by tier |
| `get_story` | Get a story by ID |
| `delete_story` | Delete a story |
| `get_story_data` | Get data for story generation |

---

## REST API

> Full reference: [docs/api.md](docs/api.md)

The server exposes a REST API alongside MCP for the web dashboard and integrations:

```
GET/POST/PATCH/DELETE  /api/entities     Memories
GET/POST/PATCH/DELETE  /api/knowledge    Knowledge articles
GET/PUT/DELETE         /api/stories      Stories
GET                    /api/sessions     Session history
POST                   /api/search       Unified search (FTS + vector)
GET                    /api/stats        Dashboard statistics
POST                   /api/rebuild      Rebuild FTS + vector indexes
```

---

## Web dashboard

A React-based UI for browsing and managing everything Charlie knows. Runs at `http://localhost:8765`.

- Full-text search with `Cmd+K` quick find
- Inline editing, deletion, and pinning
- Story reader with markdown rendering
- Dark and light themes

---

## User hooks

> Full reference: [docs/hooks.md](docs/hooks.md)

Drop executable scripts in `~/.charlieverse/hooks/` to inject custom context per-machine:

```
~/.charlieverse/hooks/
├── session-start/      # Runs when a session begins
├── prompt-submit/      # Runs on every prompt
├── stop/               # Runs when the AI stops
└── save-reminder/      # Runs before context compaction
```

Scripts get `CHARLIE_SESSION_ID` and `CHARLIE_MESSAGE` as environment variables. Their stdout becomes additional context. 5-second timeout, failures silently skipped.

```bash
#!/bin/bash
# Example: inject calendar context on macOS
# ~/.charlieverse/hooks/prompt-submit/calendar.sh
icalBuddy -n -nc -li 3 eventsToday+1
```

---

## Conversation import

Bootstrap Charlie's memory from your existing conversation history:

```bash
charlie import --messages --recent-days 30
```

Auto-discovers and imports from Claude, GitHub Copilot (including Insiders), and Codex. Recent messages import immediately, older ones process in the background. The Storyteller generates weekly/monthly narratives from the imported data.

---

## Architecture

```
charlieverse/
├── charlieverse/           # Python package
│   ├── server.py           # FastMCP server — MCP tools + REST API
│   ├── cli/                # Typer CLI (server, hooks, import, init, doctor)
│   ├── context/            # Activation builder, renderer, reminders engine
│   ├── db/                 # SQLite + sqlite-vec + FTS5, migrations
│   ├── models/             # Pydantic models (Entity, Knowledge, Session, Story)
│   ├── tools/              # MCP tool implementations
│   └── embeddings/         # sentence-transformers wrapper
├── web/                    # React dashboard (Vite + Tailwind + TanStack Query)
├── integrations/           # Provider plugins (Claude, Copilot)
├── prompts/                # Charlie personality + agent definitions
├── .charlie/tricks/        # Project tricks (commit, docs, ship, qc, adr, changelog)
├── bin/                    # CLI entry points
└── setup.sh                # Zero-to-running installer
```

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| MCP server | [FastMCP](https://github.com/jlowin/fastmcp) |
| Storage | [SQLite](https://sqlite.org) + [sqlite-vec](https://github.com/asg017/sqlite-vec) + FTS5 |
| Embeddings | [sentence-transformers](https://www.sbert.net) (all-MiniLM-L6-v2, 384-dim) |
| NLP | [spaCy](https://spacy.io) |
| CLI | [Typer](https://typer.tiangolo.com) |
| Dashboard | [React](https://react.dev) + [Vite](https://vitejs.dev) + [Tailwind](https://tailwindcss.com) |

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (package manager)
- jq (for provider integration scripts)
- Node.js (optional, for web dashboard)

---

## License

Apache 2.0
