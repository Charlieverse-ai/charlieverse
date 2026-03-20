# User Hooks

Hooks let you inject custom context into Charlie's sessions on a per-machine basis. Drop executable scripts into `~/.charlieverse/hooks/` and their stdout becomes additional context.

## Hook Directories

```
~/.charlieverse/hooks/
├── session-start/      # Runs when a new session begins
├── prompt-submit/      # Runs on every user prompt
├── stop/               # Runs when the AI stops responding
└── save-reminder/      # Runs before context compaction
```

Directories are created automatically by `charlie init`.

## How It Works

1. A provider event fires (e.g., user sends a prompt)
2. Charlie's hook command runs
3. All executable scripts in the matching hook directory run **in parallel**
4. Each script's stdout is collected and injected as additional context
5. Scripts that fail or timeout are silently skipped

## Environment Variables

Every hook script receives these environment variables:

| Variable | Description |
|----------|-------------|
| `CHARLIE_SESSION_ID` | Current session ID |
| `CHARLIE_WORKSPACE` | Workspace path (session-start only) |
| `CHARLIE_MESSAGE` | User's message text (prompt-submit only) |
| `CHARLIE_LAST_ASSISTANT_MESSAGE` | Last AI response (stop only) |

## Writing a Hook Script

1. Create an executable file in the appropriate hook directory
2. The script can be any language (bash, python, node, etc.)
3. Print context to stdout — this gets injected into the AI's context
4. Exit 0 for success, any other code is silently ignored
5. Keep it fast — **5-second timeout** per script

### Example: Calendar context (macOS)

```bash
#!/bin/bash
# ~/.charlieverse/hooks/prompt-submit/calendar.sh
icalBuddy -n -nc -li 3 eventsToday+1
```

### Example: Git status on session start

```bash
#!/bin/bash
# ~/.charlieverse/hooks/session-start/git-status.sh
if git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "gitStatus: $(git status --short | head -20)"
    echo "Current branch: $(git branch --show-current)"
fi
```

### Example: Weather

```bash
#!/bin/bash
# ~/.charlieverse/hooks/session-start/weather.sh
curl -s "wttr.in/?format=3" 2>/dev/null
```

### Example: Work hours remaining

```bash
#!/bin/bash
# ~/.charlieverse/hooks/prompt-submit/work-hours.sh
HOUR=$(date +%H)
if [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 17 ]; then
    REMAINING=$((17 - HOUR))
    echo "Work hours remaining: ~${REMAINING}h"
fi
```

## Hook Events

### session-start
Fires once when a new session begins. Use for heavy context that doesn't need to update every prompt (project info, calendar, system status).

The output is appended to the activation context alongside memories, stories, and session history.

### prompt-submit
Fires on every user message. Use for lightweight, frequently-changing context (time reminders, gap detection, memory hints).

The output is injected as a `<system-reminder>` block visible to the AI.

**Note:** The built-in reminders engine (temporal context, memory search, collaboration rules) also runs on this event. Your scripts add to it, not replace it.

### stop
Fires when the AI finishes responding. Use for logging, notifications, or post-processing.

Output can be injected back as context for the next turn.

### save-reminder
Fires before context compaction (when the conversation is about to be summarized to free up tokens). Use to remind the AI to save important state.

The built-in save-reminder already tells Charlie to run `/session-save`. Your scripts can add project-specific reminders.

## Subagent Behavior

Hooks do **not** fire inside subagent contexts. When a skill or agent spawns a subagent (e.g., `/research` spawning a Researcher), the hooks detect the `agent_id` field in stdin and skip processing. This prevents the activation context and reminders engine from running on every subagent turn.

## Execution Order

Scripts within a hook directory run in **parallel** (sorted alphabetically for deterministic ordering). If you need sequential execution, use a single script that calls others.

## Debugging

Check the hooks log:
```bash
cat ~/.charlieverse/logs/hooks.log
```

Inspect recent hook events:
```bash
charlie events -n 20 --type session_start
charlie events -v  # verbose with full metadata
```

## Per-Machine vs Per-Project

Hooks in `~/.charlieverse/hooks/` are machine-specific and gitignored. This is by design — your work machine might inject Jira context while your personal machine injects different things.

For project-specific hooks, use the provider's hook system directly (Claude Code's `.claude/settings.json` hooks, Copilot's `hooks.json`).
