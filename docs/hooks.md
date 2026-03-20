# User Hooks

Hooks let you inject custom context into Charlie's sessions on a per-machine basis. Drop executable scripts into `~/.charlieverse/hooks/` and their stdout becomes additional context.

---

## Hook directories

```
~/.charlieverse/hooks/
├── session-start/      # Runs when a new session begins
├── prompt-submit/      # Runs on every user prompt
├── stop/               # Runs when the AI stops responding
└── save-reminder/      # Runs before context compaction
```

Directories are created automatically by `charlie init`.

---

## How it works

1. A provider event fires (e.g., user sends a prompt)
2. Charlie's hook command runs
3. All executable scripts in the matching directory run **in parallel**
4. Each script's stdout is collected and injected as additional context
5. Scripts that fail or timeout are silently skipped

---

## Environment variables

Every hook script receives:

| Variable | Available in | Description |
|----------|-------------|-------------|
| `CHARLIE_SESSION_ID` | all hooks | Current session ID |
| `CHARLIE_WORKSPACE` | session-start | Workspace path |
| `CHARLIE_MESSAGE` | prompt-submit | User's message text |
| `CHARLIE_LAST_ASSISTANT_MESSAGE` | stop | Last AI response |

---

## Writing a hook script

1. Create an executable file in the appropriate hook directory
2. Any language works (bash, python, node, etc.)
3. Print context to stdout — this gets injected into the AI's context
4. Exit 0 for success; any other code is silently ignored
5. Keep it fast — **5-second timeout** per script

---

## Examples

**Calendar context (macOS)**

```bash
#!/bin/bash
# ~/.charlieverse/hooks/prompt-submit/calendar.sh
icalBuddy -n -nc -li 3 eventsToday+1
```

**Git status on session start**

```bash
#!/bin/bash
# ~/.charlieverse/hooks/session-start/git-status.sh
if git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "gitStatus: $(git status --short | head -20)"
    echo "Current branch: $(git branch --show-current)"
fi
```

**Weather**

```bash
#!/bin/bash
# ~/.charlieverse/hooks/session-start/weather.sh
curl -s "wttr.in/?format=3" 2>/dev/null
```

**Work hours remaining**

```bash
#!/bin/bash
# ~/.charlieverse/hooks/prompt-submit/work-hours.sh
HOUR=$(date +%H)
if [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 17 ]; then
    REMAINING=$((17 - HOUR))
    echo "Work hours remaining: ~${REMAINING}h"
fi
```

---

## Hook events

### session-start

Fires once when a new session begins. Use for heavy context that doesn't need to update every prompt (project info, calendar, system status).

Output is appended to the activation context alongside memories, stories, and session history.

### prompt-submit

Fires on every user message. Use for lightweight, frequently-changing context (time reminders, gap detection, memory hints).

Output is injected as a `<system-reminder>` block visible to the AI.

> The built-in reminders engine (temporal context, memory search, collaboration rules) also runs on this event. Your scripts add to it, not replace it.

### stop

Fires when the AI finishes responding. Use for logging, notifications, or post-processing.

Output can be injected back as context for the next turn.

### save-reminder

Fires before context compaction (when the conversation is about to be summarized to free up tokens). Use to remind the AI to save important state.

> The built-in save-reminder already tells Charlie to run `/session-save`. Your scripts can add project-specific reminders.

---

## Subagent behavior

Hooks do **not** fire inside subagent contexts. When a skill or agent spawns a subagent (e.g., `/research` spawning a Researcher), the hooks detect the `agent_id` field in stdin and skip processing. This prevents the activation context and reminders engine from running on every subagent turn.

---

## Execution order

Scripts within a hook directory run in **parallel** (sorted alphabetically for deterministic ordering). If you need sequential execution, use a single script that calls others.

---

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

---

## Per-machine vs per-project

Hooks in `~/.charlieverse/hooks/` are machine-specific and gitignored. This is by design — your work machine might inject Jira context while your personal machine injects different things.

For project-specific hooks, use the provider's hook system directly (Claude Code's `.claude/settings.json` hooks, Copilot's `hooks.json`).
