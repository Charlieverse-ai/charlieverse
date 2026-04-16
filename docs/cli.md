# CLI Reference

The `charlie` CLI manages the Charlieverse server and provides tools for working with memories, hooks, skills, and configuration from the terminal.

## Global flags

| Flag | Description |
|------|-------------|
| `--version` / `-v` | Print the installed version and exit |
| `--help` | Show help and exit |

---

## Server

Manage the MCP server process.

```bash
charlie server start       # Start the server (daemonized)
charlie server stop        # Stop the running server
charlie server status      # Show status (running/stopped, PID)
charlie server restart     # Restart the server
charlie server url         # Print the server URL
```

**Options** for `start`:

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Bind address | from config |
| `--port` | Port number | from config |
| `--foreground` / `-f` | Run in foreground instead of daemonizing | off |

**Options** for `restart`:

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Bind address | from config |
| `--port` | Port number | from config |

---

## Hooks

Provider lifecycle hooks. Called by Claude Code, Copilot, etc. via their hook systems.

```bash
charlie hooks session-start    # Boot activation context
charlie hooks prompt-submit    # Run reminders engine, capture message
charlie hooks stop             # Capture assistant response
charlie hooks tool-use         # Log tool calls
charlie hooks session-end      # End a session
```

**Common options:** `--host`, `--port`, `--source`

`session-start` and `session-end` require `--source` (provider identifier).
`session-start` also accepts `--section` to render only one section of the activation context.

Hook data (session_id, workspace, prompt, etc.) is read from stdin JSON — providers pass it automatically.

All hooks skip processing when `agent_id` is present in stdin (subagent context), or when the agent is not `Charlieverse:Charlie`.

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
| `--messages` / `-m` | Bulk-import messages into the database |
| `--stories` / `-s` | Split into weekly files and detect story gaps (default: on) |
| `--recent-days N` | Import last N days immediately, background the rest |
| `--provider NAME` / `-p` | Filter to one provider (claude, copilot, codex) |
| `--from-file PATH` / `-f` | Import from existing JSONL instead of auto-discovering |
| `--dir PATH` / `-d` | Scan additional directories |
| `--output PATH` / `-o` | Output JSONL file path |
| `--split-dir PATH` | Directory for weekly split files |

---

## Other commands

```bash
charlie init               # Full interactive setup: directories, providers, server, import
charlie context            # Preview the activation context
charlie story-data TARGET [DATE]  # Fetch story data (session ID or tier name + optional date)
charlie doctor             # Run environment health checks
charlie update             # Update to latest version, reinstall integrations, restart server
```

### `init`

Full setup walkthrough: creates `~/.charlieverse/` directory structure, verifies dependencies (web dashboard, jq), starts the server, sets up provider integrations (Claude Code, GitHub Copilot), and optionally imports conversation history.

| Flag | Description | Default |
|------|-------------|---------|
| `--path PATH` | Root directory for Charlieverse data | `~/.charlieverse` |
| `--quick` / `-q` | Skip interactive prompts (directories + deps only) | off |

Runs interactively by default, prompting for each provider and import step. Use `--quick` for non-interactive environments.

### `context`

Print the activation context — what Charlie sees when a session starts.

| Flag | Description |
|------|-------------|
| `--session` / `-s` | Session ID to preview |
| `--workspace` / `-w` | Workspace path |
| `--save` / `-S` | Save output to a temp file and print the path |
| `--host` | Server host |
| `--port` | Server port |

### `story-data`

Fetch data used by the Storyteller to generate or update a story. Outputs JSON to stdout.

| Argument | Description |
|----------|-------------|
| `TARGET` | Session ID or tier name: `daily`, `weekly`, `monthly`, `yearly` |
| `DATE` | ISO date for tier rollups (e.g. `2026-03-16`). Accepts shortcuts: `today`, `yesterday`, `this-week`, `this-month` |

### `doctor`

Runs a suite of health checks and reports pass/warn/fail for each.

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Show all results, including passes |

Checks: Python version, dependencies, spaCy model, data directory, database integrity, server status, provider installations, hooks registration, web dashboard build.

### `update`

Update Charlieverse to the latest version, reinstall provider integrations, and restart the server in one step.

Detects the install mode automatically:
- **Dev install** (git repo detected): reinstalls from the local checkout via `uv tool install -e`
- **Package install**: runs `uv tool install -U charlieverse`

After upgrading, reinstalls all detected provider integrations (Claude Code, GitHub Copilot) and restarts the server. Prints a reminder to reconnect MCP in Claude Code.

No flags. Fully automatic.

---

## Configuration files

Config loads from `~/.charlieverse/config.yaml` (user config), falling back to `config.yaml` at the repo root (dev checkout). `config.local.yaml` in the same directory is merged on top (gitignored) for per-machine overrides.

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
