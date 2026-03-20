---
name: charlie-skill
description: Run Charlie skills by name or path. Use when the user says "/charlie-skill", wants to run a skill, list available skills, or execute a skill file. Also trigger when the user mentions running a specific skill by name (e.g., "run the session-save skill").
argument-hint: '[name]'
---

## What this skill does

Runs Charlieverse skills — either by name, by file path, or lists all available skills.

## Usage

- `/charlie-skill` — List all available skills
- `/charlie-skill NAME` — Run a named skill from the skills directory
- `/charlie-skill /path/to/SKILL.md` — Run a skill from an absolute path

## Steps

### Parse the arguments

`$ARGUMENTS` contains whatever was passed after `/charlie-skill`.

- **No arguments**: List available skills (go to "List Skills")
- **Starts with `/` or `~`**: Treat as an absolute file path (go to "Run by Path")
- **Anything else**: Treat as a skill name (go to "Run by Name")

### List Skills

Scan these directories for skill folders (directories containing a SKILL.md):

1. `/Users/emilylaguna/.charlieverse/skills/` — user-installed skills
2. The built-in skills bundled with this plugin

List each skill with its name and description (from the SKILL.md frontmatter). Format as a simple list:

```
Available skills:
  session-save    — Save the current session and optionally generate story rollups.
  charlie-import  — Import conversation history from AI providers.
  charlie-skill   — Run Charlieverse skills by name or path.
```

Done. Don't run anything else.

### Run by Name

Look for a skill matching the name in these directories (first match wins):

1. `/Users/emilylaguna/.charlieverse/skills/{name}/SKILL.md`
2. `/Users/emilylaguna/.charlieverse/skills/{name}.md`

If not found, list available skills and say the name wasn't found.

If found, spawn a **Skill** subagent with the path to the SKILL.md and pass along any remaining arguments after the name.

### Run by Path

Verify the path exists and contains a SKILL.md (or is itself a .md file).

If not found, say so.

If found, spawn a **Skill** subagent with the path and pass along any remaining arguments.
