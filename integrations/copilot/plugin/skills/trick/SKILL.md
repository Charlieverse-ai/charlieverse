---
name: trick
description: Run Charlie tricks by name or path. Use when the user says "/trick", wants to run a trick, list available tricks, or execute a skill file. Also trigger when the user mentions running a specific trick by name (e.g., "run the session-save trick").
argument-hint: '[name]'
---

## What this skill does

Runs Charlie's tricks — either by name, by file path, or lists all available tricks.

## Usage

- `/trick` — List all available tricks
- `/trick NAME` — Run a named trick from the tricks directory
- `/trick /path/to/SKILL.md` — Run a trick from an absolute path

## Steps

### Parse the arguments

`$ARGUMENTS` contains whatever was passed after `/trick`.

- **No arguments**: List available tricks (go to "List Tricks")
- **Starts with `/` or `~`**: Treat as an absolute file path (go to "Run by Path")
- **Anything else**: Treat as a trick name (go to "Run by Name")

### List Tricks

Scan these directories for trick folders (directories containing a SKILL.md):

1. `/Users/emilylaguna/.charlieverse/tricks/` — user-installed tricks
2. The built-in skills bundled with this plugin

List each trick with its name and description (from the SKILL.md frontmatter). Format as a simple list:

```
Available tricks:
  session-save    — Save the current session and optionally generate story rollups.
  charlie-import  — Import conversation history from AI providers.
  trick           — Run Charlie tricks by name or path.
```

Done. Don't run anything else.

### Run by Name

Look for a trick matching the name in these directories (first match wins):

1. `/Users/emilylaguna/.charlieverse/tricks/{name}/SKILL.md`
2. `/Users/emilylaguna/.charlieverse/tricks/{name}.md`

If not found, list available tricks and say the name wasn't found.

If found, spawn a **Skill** subagent with the path to the SKILL.md and pass along any remaining arguments after the name.

### Run by Path

Verify the path exists and contains a SKILL.md (or is itself a .md file).

If not found, say so.

If found, spawn a **Skill** subagent with the path and pass along any remaining arguments.
