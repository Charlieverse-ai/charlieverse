# Troubleshooting

Symptom, cause, fix. In that order.

---

## Server Won't Start

**Symptom:** `charlie server start` returns an error or the server doesn't respond after startup.

### Port already in use

```
Failed to start Charlieverse
```

The server attempts to kill any orphan process holding port 8765 automatically. If it still fails:

```bash
lsof -ti :8765          # find what's holding the port
kill -9 $(lsof -ti :8765)
charlie server start
```

To use a different port, set it in `config.local.yaml`:

```yaml
server:
  port: 9000
```

Then re-run the integration install scripts so hooks and MCP config pick up the new port.

### Orphan PID file

The PID file says it's running, but the process is dead:

```bash
cat ~/.charlieverse/run/charlie.pid   # see the claimed PID
ps aux | grep charlieverse            # check if that PID exists
rm ~/.charlieverse/run/charlie.pid    # clear stale PID
charlie server start
```

### Wrong Python version

```bash
python3 --version    # must be 3.12+
uv python list       # see what uv sees
```

Install Python 3.12 and re-run `uv sync`.

### Startup errors in log

```bash
tail -50 ~/.charlieverse/logs/charlie.log
```

The server log is the first place to look for any startup failure. Module import errors, migration failures, and port bind errors all appear here.

---

## Hooks Not Firing

**Symptom:** No activation context on session start, no reminders on prompts, memories not being saved automatically.

### settings.json not configured (Claude Code)

```bash
cat ~/.claude/settings.json | grep hooks
```

If there are no hook entries, re-run the integration:

```bash
./integrations/claude/install.sh
```

This merges the hooks configuration into `~/.claude/settings.json`. The hooks block should reference `charlie hooks session-start`, `prompt-submit`, `stop`, `tool-use`, and `save-reminder`.

### Wrong paths in hooks config

Hooks reference the full absolute path to the `charlie` CLI. If you moved the repo:

```bash
charlie config hooks   # shows the hooks data directory
cat ~/.charlieverse/integrations/claude/hooks/hooks.json
```

The command paths should point to the current `bin/charlie` location. Re-run `./integrations/claude/install.sh` to regenerate with correct paths.

### Subagent silencing

Hooks intentionally skip when `agent_id` is present in stdin. This is correct behavior — hooks should not fire inside subagent contexts (research agents, skill executors, etc.). If activation context is missing only in subagent sessions, that is expected.

### Hooks log

```bash
tail -50 ~/.charlieverse/logs/hooks.log
charlie events -n 20   # recent hook events
charlie events --type session_start -v   # verbose session-start events
```

### Copilot hooks format

Copilot uses a flat hook format (no `hooks`/`matcher` wrapper). The Copilot install script generates the correct format. If you edited `hooks.json` manually, compare against the generated file at `integrations/copilot/plugin/hooks/hooks.json`.

---

## MCP Connection Fails

**Symptom:** The AI tool reports it cannot connect to the MCP server, or MCP tools are unavailable.

### Server not running

```bash
charlie server status
charlie server start
```

The server must be running before opening a chat session.

### Wrong MCP URL in provider config

```bash
charlie config mcp      # shows the expected MCP URL (e.g. http://127.0.0.1:8765/mcp)
```

For Claude Code, check `~/.charlieverse/integrations/claude/.mcp.json`. For Copilot, check `integrations/copilot/plugin/.mcp.json`. Both should match `charlie config mcp`.

Re-run the relevant install script to regenerate:

```bash
./integrations/claude/install.sh
./integrations/copilot/install.sh
```

### Firewall or network issue

The server binds to `127.0.0.1` by default. If your tool runs in a container or remote environment, set `host: "0.0.0.0"` in `config.local.yaml` and confirm firewall rules allow the port.

### Health check

```bash
curl http://127.0.0.1:8765/health
```

A `200 OK` response confirms the server is up and reachable.

---

## Activation Context Is Empty

**Symptom:** Charlie starts a session with no memories, no session history, no context — not even the birthday letter.

### First run detection

On first run (no sessions, memories, or stories in the database), the birthday letter is delivered instead of activation context. This is correct. Charlie has no history yet.

After the first session, run `/session-save` so the session is stored. From the next session, activation context will load.

### Server unreachable during session-start

If `charlie hooks session-start` cannot reach the server, it exits with an error and no context is injected. Check:

```bash
charlie server status
tail -20 ~/.charlieverse/logs/hooks.log
```

### Preview activation context

```bash
charlie context
```

This prints what the current activation context would look like without starting a session.

---

## Web Dashboard Won't Load

**Symptom:** `http://localhost:8765` shows an error or blank page.

### npm build not run

```bash
ls /path/to/charlieverse/web/dist/
```

If `dist/` is missing or empty, the frontend was never built:

```bash
charlie init    # re-runs npm install + npm run build
```

Or manually:

```bash
cd /path/to/charlieverse/web
npm install
npm run build
```

### npm not installed

`charlie init` skips the web build if npm is not found. Install Node.js (`brew install node`), then re-run `charlie init`.

### Server not running

The dashboard is served by the same process as the MCP server. If the server is stopped, the dashboard is unavailable.

```bash
charlie server start
```

---

## Provider-Specific Issues

### Claude Code: plugin not installed

```bash
claude plugin list | grep charlieverse
```

If not listed:

```bash
./integrations/claude/install.sh
```

The script registers the local plugin marketplace and installs the Charlieverse plugin. Requires the `claude` CLI to be installed.

### Claude Code: `claude` CLI not found

The integration script requires the `claude` CLI in PATH. Install it from the [Claude Code documentation](https://docs.anthropic.com/claude-code), then re-run `./integrations/claude/install.sh`.

### Copilot: plugin location not registered

The Copilot install script cannot write VS Code's JSONC settings file automatically. After running `./integrations/copilot/install.sh`, you must manually add the output block to VS Code user settings:

`Cmd+Shift+P` → `Preferences: Open User Settings (JSON)`

```json
"chat.pluginLocations": {
  "/absolute/path/to/charlieverse/integrations/copilot/plugin": true
},
"chat.plugins.enabled": true
```

### Cursor

Cursor support is not yet available via an install script. Use the manual MCP config path:

```json
{
  "mcpServers": {
    "charlie-tools": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Place this in your Cursor MCP config. Hooks are not yet integrated for Cursor.

---

## Database Issues

**Symptom:** Server fails to start with a database error, or queries return malformed results.

### Check the log first

```bash
tail -50 ~/.charlieverse/logs/charlie.log
```

Migration errors, sqlite-vec extension load failures, and schema mismatches all appear here.

### Rebuild FTS and vector indexes

FTS5 and vector indexes can be rebuilt without data loss:

```bash
curl -X POST http://127.0.0.1:8765/api/rebuild
```

This is safe to run at any time. Use it if search returns stale or missing results.

### Database path

```bash
charlie config database   # prints the full path to charlie.db
```

### Backup location

Backups are stored in `~/.charlieverse/backups/`. The server does not auto-backup — copy `charlie.db` manually before any destructive operations.

### Corrupt or malformed database

If migrations fail or the database is corrupt, the safest recovery is to restore from a backup or reinitialize:

```bash
cp ~/.charlieverse/charlie.db ~/.charlieverse/backups/charlie.db.manual-backup
rm ~/.charlieverse/charlie.db
charlie server restart    # migrations run on next connect, creating a fresh database
```

All memory data will be lost unless restored from backup.

---

## Diagnostic Commands

Quick status check:

```bash
charlie server status
charlie config
charlie events -n 10
```

Tail all logs:

```bash
tail -f ~/.charlieverse/logs/charlie.log
tail -f ~/.charlieverse/logs/hooks.log
```

Preview activation context without a session:

```bash
charlie context
```

Check server health:

```bash
curl -s http://127.0.0.1:8765/health
```
