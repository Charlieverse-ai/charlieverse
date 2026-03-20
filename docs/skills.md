# Tricks Reference

Tricks are Charlie's name for portable capability packages that agents load on demand. They follow the [AgentSkills.io SKILL.md standard](https://agentskills.io/specification) for maximum compatibility.

---

## Bundled skills

These ship with the Charlieverse repo in `prompts/skills/` and are available to any compatible provider.

### `research`

Research a topic and save findings to knowledge.

**Usage:** `/research [topic]`

1. Searches existing knowledge for the topic
2. Spawns a Researcher subagent for fresh research
3. Creates or updates knowledge with findings
4. Returns a summary

### `trick`

Run Charlie tricks by name or path.

**Usage:** `/trick [name or path]`

- No args: lists available tricks via `charlie trick list`
- Name: resolves the trick, spawns Skill agent with it
- Supports provider delegation: `/trick [name] [provider]`

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
