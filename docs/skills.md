# Skills Reference

Skills are portable capability packages that agents load on demand. Charlieverse ships with several bundled skills.

## Bundled Skills

### session-save
Save the current session and optionally generate story rollups.

**Usage:** `/session-save [cascade]`

Steps:
1. Calls `session_update` with session summary
2. Checks if a daily story needs updating
3. If "cascade" or "full" in arguments, generates weekly and monthly rollups via Storyteller

### charlie-import
Import conversation history from AI providers.

**Usage:** Triggered automatically on first session, or manually.

Steps:
1. Auto-discovers Claude, Copilot, Codex, Cursor session files
2. Extracts messages into JSONL
3. Bulk-imports into database
4. Detects story gaps and spawns Storyteller to fill them

### research
Research a topic and save findings to knowledge.

**Usage:** `/research [topic]`

Steps:
1. Searches existing knowledge for the topic
2. Spawns a Researcher subagent for fresh research
3. Creates or updates knowledge with findings
4. Returns a summary

### charlie-skill
Run skills by name or path.

**Usage:** `/charlie-skill [name or path]`

Steps:
1. No args → lists available skills via `charlie skill list`
2. Name → resolves via `charlie skill find`, spawns Skill agent
3. Path → spawns Skill agent directly

### codex
Delegate a task to OpenAI Codex CLI.

**Usage:** `/codex [task]`

Forks context and spawns the Codex CLI agent, which runs `codex exec` in non-interactive mode.

### copilot
Delegate a task to GitHub Copilot CLI.

**Usage:** `/copilot [task]`

Forks context and spawns the Copilot CLI agent, which runs `copilot -p` in non-interactive mode.

## Creating Skills

Skills follow the [AgentSkills.io open standard](https://agentskills.io/specification).

A skill is a directory containing a `SKILL.md`:

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

Required fields: `name` (lowercase, hyphens, must match directory), `description`.

### Installation

Drop the skill directory into any of these locations:
- `~/.charlieverse/skills/` — Charlie-managed
- `.charlie/skills/` — project-local (gitignored)
- `~/.agents/skills/` — cross-platform standard
- Provider-specific paths (`~/.claude/skills/`, `~/.copilot/skills/`, etc.)

Run `charlie skill list` to verify it's discovered.
