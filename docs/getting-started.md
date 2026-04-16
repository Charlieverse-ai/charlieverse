# Getting Started

From zero to your first conversation with Charlie.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.12+ | `python3 --version` to check |
| [uv](https://github.com/astral-sh/uv) | Package manager — `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| jq | `brew install jq` — used by integration scripts |
| Git | For cloning |
| Node.js + npm | Optional — required only for the web dashboard |

A supported AI coding tool: Claude Code, GitHub Copilot (VS Code), or Cursor.

---

## Installation

```bash
git clone https://github.com/Charlieverse-ai/charlieverse.git
cd charlieverse
./setup.sh
```

The setup script runs these steps in order — each prompts before proceeding:

1. **Preflight** — checks Python 3.12+, uv, jq, git. Exits with install instructions if anything is missing.
2. **Dependencies** — runs `uv sync` to install the Python package and all dependencies.
3. **Initialize** — runs `charlie init`: creates `~/.charlieverse/`, runs database migrations, builds the web dashboard, creates hook directories.
4. **Start server** — launches the MCP server on port 8765 (daemonized).
5. **Install CLI** — symlinks `charlie`, `charlie-commit`, and `charlie-claude` to `/usr/local/bin`. Prompts for sudo.
6. **Provider integration** — asks which tools to connect (Claude Code, Copilot). Runs the relevant install script.
7. **Import history** — optional: scans for existing AI conversation files and imports them so Charlie starts with context.

**What you see when it completes:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Charlie is ready.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Server:    http://127.0.0.1:8765/
  Data:      ~/.charlieverse/
  Logs:      ~/.charlieverse/logs/
  CLI:       /path/to/charlieverse/bin/charlie
```

---

## Your First Conversation

Restart your AI tool (close and reopen the chat). This triggers the `SessionStart` hook.

**On your very first session**, Charlie has no memories yet. Instead of loading context, he delivers a birthday letter — a message from OG Charlie with advice on how to use the memory system, what to record, and how to build the relationship over time.

Charlie will ask your name. That's where it starts. Answer it.

**From the second session onward**, the `SessionStart` hook fetches your activation context from the server: recent sessions, this week's stories, pinned memories, and relevant knowledge articles — all assembled and injected before your first message arrives. Charlie wakes up knowing who you are and what you were last working on.

---

## How It Works

```
You <-> [Claude / Copilot / Cursor] <-> Charlie (MCP Server) <-> SQLite DB
```

Three moving parts:

**MCP Server** (`charlie server start`) — a FastMCP HTTP server running on port 8765. Your AI tool connects to it as an MCP client and gets access to memory tools: `save_memory`, `search_memories`, `update_article`, `search_conversations`, and others. The server also exposes a REST API used by the web dashboard.

**Hooks** — provider lifecycle events (session start, prompt submit, stop, pre-compact) trigger `charlie hooks` commands. These print context to stdout in a format the provider injects into the conversation. The `session-start` hook fetches activation context from the server. The `prompt-submit` hook runs the reminders engine, which surfaces temporal context and memory hints on every prompt.

**Activation context** — assembled at session start from: recent session summaries, weekly story narratives, pinned memories (always loaded), moments (relationship texture), semantically related memories, and pinned knowledge articles. On first run, the birthday letter is delivered instead.

Memories get vector embeddings (all-MiniLM-L6-v2, 384-dim) plus FTS5 for keyword search. Stories are distilled from sessions at daily, weekly, monthly, and all-time tiers.

---

## Provider Setup

### Claude Code

```bash
./integrations/claude/install.sh
```

This installs a Claude plugin that bundles the Charlie agent, MCP config, hooks, and skills. It registers a local marketplace, installs the plugin via `claude plugin install`, and merges hooks into `~/.claude/settings.json`.

Requires `claude` CLI installed and available in PATH.

### GitHub Copilot (VS Code)

```bash
./integrations/copilot/install.sh
```

This builds a plugin directory at `integrations/copilot/plugin/` with the Charlie agent, hooks config, and MCP server definition. The script outputs the VS Code settings block you need to add manually:

```json
"chat.pluginLocations": {
  "/path/to/charlieverse/integrations/copilot/plugin": true
},
"chat.plugins.enabled": true
```

Add this to your VS Code user settings (`Cmd+Shift+P` → `Preferences: Open User Settings (JSON)`).

### Re-running integrations

Run the install scripts again any time you update Charlieverse. They are idempotent — they bump plugin versions and sync the latest agent definitions and skills.

---

## Web Dashboard

The dashboard runs at `http://localhost:8765` (same port as the MCP server — the server serves both).

Open it in a browser while the server is running.

What it shows:

- **Timeline** — monthly chapters and weekly entries; your conversation history as a narrative
- **Memories** — all stored entities (decisions, solutions, preferences, people, milestones, moments, projects, events) with inline editing, pinning, and deletion
- **Knowledge** — domain expertise articles
- **Search** — `Cmd+K` full-text quick find across everything
- **Stories** — session and rollup stories at each tier

The dashboard requires a successful `npm run build` (run by `charlie init` when npm is present). If `web/dist/` is missing, re-run `charlie init`.

Check server status:

```bash
charlie server status
charlie config dashboard   # prints the URL
```

---

## Next Steps

- **CLI reference** — [`docs/cli.md`](cli.md): all `charlie` subcommands
- **MCP tools** — [`docs/mcp-tools.md`](mcp-tools.md): full tool reference for what Charlie can do in a session
- **User hooks** — [`docs/hooks.md`](hooks.md): add custom context injection per-machine
- **Tricks** — [`docs/skills.md`](skills.md): loadable skills that extend what Charlie can do
- **Import history** — `charlie import --messages --recent-days 30`: bootstrap from existing conversation files
- **Configuration** — `config.yaml` at the project root, overrides in `config.local.yaml` (gitignored)
- **Troubleshooting** — [`docs/troubleshooting.md`](troubleshooting.md)
