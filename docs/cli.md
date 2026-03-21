# CLI Reference

The `charlie` CLI manages the Charlieverse server and provides tools for working with memories, hooks, skills, and configuration from the terminal.

---

## Server

Manage the MCP server process.

```bash
charlie server start       # Start the server (daemonized)
charlie server stop        # Stop the running server
charlie server status      # Show status (running/stopped, PID, URL)
charlie server restart     # Restart the server
charlie server url         # Print the server URL
```

**Options** for `start`:

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Bind address | from config |
| `--port` | Port number | from config |
| `--foreground` / `-f` | Run in foreground instead of daemonizing | off |
| `--transport` | Transport type: `http`, `sse`, or `stdio` | `http` |

**Options** for `restart`:

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Bind address | from config |
| `--port` | Port number | from config |
| `--transport` | Transport type: `http`, `sse`, or `stdio` | `http` |

---

## Hooks

Provider lifecycle hooks. Called by Claude Code, Copilot, etc. via their hook systems.

```bash
charlie hooks session-start    # Boot activation context
charlie hooks prompt-submit    # Run reminders engine, capture message
charlie hooks stop             # Capture assistant response
charlie hooks tool-use         # Log tool calls
charlie hooks save-reminder    # Remind to save before compaction
charlie hooks session-end      # End a session
```

**Common options:** `--host`, `--port`, `--source`

`session-start` also accepts `--workspace` and `--session-id` (optional — both can be read from stdin JSON instead).
`session-end` requires `--session-id`.

All hooks skip processing when `agent_id` is present in stdin (subagent context).

---

## Config

View and inspect configuration.

```bash
charlie config             # Show all config values as a table
charlie config path        # Charlieverse data path
charlie config database    # Database path
charlie config logs        # Logs directory
charlie config hooks       # Hooks directory
charlie config dashboard   # Dashboard URL
charlie config mcp         # MCP endpoint URL
charlie config api         # API base URL
```

---

## Tricks

Discover and inspect Charlie's tricks (and provider skills).

```bash
charlie trick              # Show help
charlie trick list         # List all discovered tricks and skills
charlie trick list --json  # List as JSON
charlie trick find NAME    # Print path to a trick's SKILL.md
charlie trick info NAME    # Show metadata (panel with description, source, tools, files)
charlie trick read NAME    # Print full SKILL.md contents
```

### Discovery paths

Tricks and skills are auto-discovered from these locations, in order:

1. `~/.charlieverse/tricks/` — Charlie-managed
2. `.charlie/tricks/` — project-local
3. `~/.agents/skills/` — cross-platform standard
4. Provider paths: `~/.copilot/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`, `~/.gemini/skills/`
5. Project-level: `.agents/skills/`, `.claude/skills/`, `.github/skills/`, `.cursor/skills/`

---

## Import

Bootstrap Charlie's memory from existing AI conversation history.

```bash
charlie import --messages --recent-days 30
```

| Flag | Description |
|------|-------------|
| `--messages` | Bulk-import messages into the database |
| `--stories` | Split into weekly files and detect story gaps |
| `--recent-days N` | Import last N days immediately, background the rest |
| `--provider NAME` | Filter to one provider (claude, copilot, codex) |
| `--from-file PATH` | Import from existing JSONL instead of auto-discovering |
| `--dir PATH` | Scan additional directories |

---

## Other commands

```bash
charlie init               # First-run setup (database, directories, web build)
charlie context            # Preview the activation context
charlie log CONTENT        # Record a logbook entry
charlie events             # List recent hook events
charlie story-data TARGET [DATE]  # Fetch story data (session ID or tier name + optional date)
charlie doctor             # Run environment health checks
```

### `events`

List recent hook events from the server.

| Flag | Description |
|------|-------------|
| `--session` / `-s` | Filter by session ID |
| `--since` | Events since this ISO datetime |
| `-n` | Max events to return (default: 50) |
| `--type` / `-t` | Filter by event type (e.g. `tool_use`, `stop`, `session_start`) |
| `--verbose` / `-v` | Show full tool input details |
| `--json` | Output raw JSON |

### `story-data`

Fetch data used by the Storyteller to generate or update a story. Outputs JSON to stdout.

| Argument | Description |
|----------|-------------|
| `TARGET` | Session ID or tier name: `daily`, `weekly`, `monthly`, `quarterly`, `yearly` |
| `DATE` | ISO date for tier rollups (e.g. `2026-03-16`). Accepts shortcuts: `today`, `yesterday`, `this-week`, `this-month` |

### `doctor`

Runs a suite of health checks and reports pass/warn/fail for each.

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Show all results, including passes |

Checks: Python version, dependencies, spaCy model, data directory, database integrity, server status, provider installations, hooks registration, web dashboard build.

---

## Configuration files

Config loads from `config.yaml` at the project root, with `config.local.yaml` merged on top (gitignored). Per-machine overrides go in the local file.

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 8765
path: "~/.charlieverse"
```

```yaml
# config.local.yaml (your overrides, gitignored)
server:
  port: 9000
```
