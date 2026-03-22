# Tricks Reference

Tricks are Charlie's name for portable capability packages that agents load on demand. They follow the [AgentSkills.io SKILL.md standard](https://agentskills.io/specification) for maximum compatibility.

---

## Project tricks

These ship with the Charlieverse repo in `.charlie/tricks/` and are available to Charlie and compatible providers when working in this project.

### `commit`

Review changes and create logical atomic commits.

**Usage:** `/commit [message]`

- No message: groups changes into logical commits and commits each separately
- With message: stages all changes and commits with that message

Uses `charlie-commit` for all commits. Never pushes.

### `docs`

Generate or update documentation from source code.

**Usage:** `/docs`

Inventories all public interfaces (CLI commands, REST API, MCP tools, bundled skills, bundled agents), then generates or updates `docs/` and `README.md`. Commits the result.

### `adr`

Extract architectural decisions from commits and record them as ADRs.

**Usage:** `/adr [commit range | "all"]`

- No args: scans the last commit
- Commit range (e.g., `HEAD~5..HEAD`): scans that range
- `all`: scans full history

Writes immutable ADR files to `docs/decisions/`. Decisions are never edited — amendments create new files.

### `changelog`

Generate or update `CHANGELOG.md` from git commits.

**Usage:** `/changelog [patch|minor|major]`

Finds commits since the last version tag, determines the version bump (from args or auto-detected from commit types), generates a changelog entry, commits it, and tags the version.

### `qc`

Run quality control checks on the codebase.

**Usage:** `/qc [all|types|tests|smoke]`

Stages: type checking (`ty check`), tests (`pytest`), server smoke test (health + REST + MCP), web dashboard check. Reports pass/fail for each stage.

### `ship`

Commit, docs, changelog, and push in one go.

**Usage:** `/ship [patch|minor|major]`

Runs: qc → commit → docs → adr → changelog → push. The full pipeline for shipping a change.

### `test-coverage`

Evaluate test coverage for recent changes.

**Usage:** `/test-coverage`

Reviews the diff from main, identifies changes that need new or updated test coverage, and updates the tests accordingly.

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
