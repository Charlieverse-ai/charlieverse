# Tricks Reference

Tricks are Charlie's name for portable capability packages that agents load on demand. They follow the [AgentSkills.io SKILL.md standard](https://agentskills.io/specification) for maximum compatibility.

---

## Bundled tricks

### `session-save`

Save the current session and optionally generate story rollups.

**Usage:** `/session-save [cascade]`

1. Calls `session_update` with a session summary
2. Checks if a daily story needs updating
3. If `cascade` or `full` in arguments, generates weekly and monthly rollups via Storyteller

### `charlie-import`

Import conversation history from AI providers.

**Usage:** Triggered automatically on first session, or manually.

1. Auto-discovers Claude, Copilot, Codex, Cursor session files
2. Extracts messages into JSONL
3. Bulk-imports into the database
4. Detects story gaps and spawns Storyteller to fill them

### `research`

Research a topic and save findings to knowledge.

**Usage:** `/research [topic]`

1. Searches existing knowledge for the topic
2. Spawns a Researcher subagent for fresh research
3. Creates or updates knowledge with findings
4. Returns a summary

### `charlie-skill`

Run skills by name or path.

**Usage:** `/charlie-skill [name or path]`

- No args: lists available skills via `charlie trick list`
- Name: resolves via `charlie skill find`, spawns Skill agent
- Path: spawns Skill agent directly

### `codex`

Delegate a task to OpenAI Codex CLI.

**Usage:** `/codex [task]`

Forks context and spawns the Codex CLI agent, which runs `codex exec` in non-interactive mode.

### `copilot`

Delegate a task to GitHub Copilot CLI.

**Usage:** `/copilot [task]`

Forks context and spawns the Copilot CLI agent, which runs `copilot -p` in non-interactive mode.

---

## Creating your own

A skill is a directory containing a `SKILL.md` file:

```
my-skill/
├── SKILL.md          # Required: YAML frontmatter + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: additional docs
└── assets/           # Optional: templates, data files
```

### SKILL.md format

```yaml
---
name: my-skill
description: What it does and when to use it.
argument-hint: '[args]'
---

## Instructions

Step-by-step workflow for the skill.
```

**Required fields:** `name` (lowercase, hyphens, must match directory name), `description`.

### Installation

Drop the skill directory into any of these locations:

| Path | Scope |
|------|-------|
| `~/.charlieverse/tricks/` | Charlie-managed (global) |
| `.charlie/tricks/` | Project-local (gitignored) |
| `~/.agents/skills/` | Cross-platform standard |
| `~/.claude/skills/`, `~/.copilot/skills/`, etc. | Provider-specific |
| `.agents/skills/`, `.github/skills/`, etc. | Project-level |

Verify discovery:

```bash
charlie trick list
```
