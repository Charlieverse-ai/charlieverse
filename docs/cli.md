# CLI Reference

The `charlie` CLI manages the Charlieverse server and provides tools for interacting with Charlie from the terminal.

## Server

| Command | Description |
|---------|-------------|
| `charlie server start` | Start the MCP server (daemonized) |
| `charlie server stop` | Stop the running server |
| `charlie server status` | Show server status (running/stopped, PID, URL) |
| `charlie server restart` | Restart the server |
| `charlie server url` | Print the server URL |

Options for `start` and `restart`:
- `--host` — Bind address (default: from config)
- `--port` — Port number (default: from config)
- `--foreground` — Run in foreground instead of daemonizing

## Hooks

Provider lifecycle hooks. Called by Claude Code, Copilot, etc. via their hook systems.

| Command | Hook Event | Description |
|---------|-----------|-------------|
| `charlie hooks session-start` | SessionStart | Boot activation context |
| `charlie hooks prompt-submit` | UserPromptSubmit | Run reminders engine, capture message |
| `charlie hooks stop` | Stop | Capture assistant response |
| `charlie hooks tool-use` | PostToolUse | Log tool calls |
| `charlie hooks save-reminder` | PreCompact | Remind to save before compaction |

Common options:
- `--host` / `--port` — Server address
- `--source` — Provider identifier (e.g., `claude-plugin`)

All hooks skip processing when `agent_id` is present in stdin (subagent context).

## Config

| Command | Description |
|---------|-------------|
| `charlie config` | Show all config values as a table |
| `charlie config path` | Print the Charlieverse data path |
| `charlie config database` | Print the database path |
| `charlie config logs` | Print the logs directory |
| `charlie config hooks` | Print the hooks directory |
| `charlie config dashboard` | Print the dashboard URL |
| `charlie config mcp` | Print the MCP endpoint URL |
| `charlie config api` | Print the API base URL |

## Skills

| Command | Description |
|---------|-------------|
| `charlie skill` | Show help |
| `charlie skill list` | List all discovered skills |
| `charlie skill list --json` | List skills as JSON |
| `charlie skill find NAME` | Print the path to a skill's SKILL.md |
| `charlie skill info NAME` | Show skill metadata (panel with description, source, tools, files) |
| `charlie skill read NAME` | Print the full SKILL.md contents |

Skills are auto-discovered from:
1. `~/.charlieverse/skills/` — Charlie-managed skills
2. `.charlie/skills/` — project-local skills
3. `~/.agents/skills/` — cross-platform standard
4. `~/.copilot/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`, `~/.gemini/skills/` — provider paths
5. `.agents/skills/`, `.claude/skills/`, `.github/skills/`, `.cursor/skills/` — project-level

## Other Commands

| Command | Description |
|---------|-------------|
| `charlie init` | First-run setup (database, directories, web build) |
| `charlie context` | Preview the activation context |
| `charlie log CONTENT` | Record a logbook entry |
| `charlie events` | List recent hook events |
| `charlie story-data TARGET` | Fetch story data (session ID or tier name) |
| `charlie import` | Import conversation history from providers |

### Import options

| Flag | Description |
|------|-------------|
| `--messages` | Bulk-import messages into the database |
| `--stories` | Split into weekly files and detect story gaps |
| `--recent-days N` | Import last N days immediately, background the rest |
| `--provider NAME` | Filter to one provider (claude, copilot, codex) |
| `--from-file PATH` | Import from existing JSONL instead of auto-discovering |
| `--dir PATH` | Scan additional directories |

## Configuration

Config loads from `config.yaml` at the project root, with `config.local.yaml` merged on top (gitignored). Per-machine overrides go in the local file.

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8765
path: "~/.charlieverse"
```

```yaml
# config.local.yaml (your overrides)
server:
  port: 9000
```
