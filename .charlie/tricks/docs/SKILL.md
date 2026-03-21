---
name: docs
description: Generate or update public documentation from source code. Use when the user says "/docs", wants to update docs, or asks to generate documentation for the project.
---

## What this skill does

Reviews all public interfaces (CLI, REST API, MCP tools, skills, agents) and generates or updates documentation in `docs/` and the README.

## Steps

### 1. Inventory public interfaces

Scan the codebase for all public-facing surfaces:

**CLI commands** — read `charlieverse/cli/main.py` to find all registered commands/typers, then read each command file for arguments, options, and help text.

**REST API endpoints** — read `charlieverse/server.py` and find all `@mcp.custom_route()` decorators. Extract method, path, and any docstrings.

**MCP tools** — read `charlieverse/server.py` and find all `@mcp.tool` decorators. Extract tool name, parameters (from type hints), and docstrings.

**Bundled skills** — run `charlie skill list --json` and read each SKILL.md for name, description, and usage.

**Bundled agents** — scan `prompts/tools/*.md` and `prompts/cli/*.md` for agent definitions. Extract name, description from frontmatter.

### 2. Check existing docs

Read `docs/` directory if it exists. Compare against the inventory to find:
- New interfaces not yet documented
- Existing docs that are stale (interface changed since doc was written)
- Docs for interfaces that no longer exist

### 3. Generate/update docs

Create or update these files:

**`docs/cli.md`** — Full CLI reference. For each command:
- Command and subcommands
- Arguments and options with types and defaults
- Description
- Examples

**`docs/api.md`** — REST API reference. For each endpoint:
- Method + path
- Request body / query params
- Response format
- Description

**`docs/mcp-tools.md`** — MCP tool reference. For each tool:
- Tool name
- Parameters with types
- Return format
- Description

**`docs/skills.md`** — Skills reference. For each bundled skill:
- Name and description
- Usage / argument hint
- What it does

**`docs/agents.md`** — Agent reference. For each bundled agent:
- Name and description
- What it's for
- How to use it

### 4. Update README

Read `README.md`. Update these sections (create if missing):
- Feature list (should reflect current capabilities)
- CLI quick reference (table of commands)
- Link to full docs in `docs/`

Don't rewrite the whole README — just update the sections that reference interfaces.

### 5. Commit

```bash
git add docs/ README.md
charlie-commit -m "Update documentation for public interfaces

Charlie 🐕 <charlie@charlieverse.ai>"
```

### Rules

- Write docs for humans, not AI. Concise, scannable, with examples.
- Use tables for parameter lists.
- Don't document internal/private interfaces.
- If an interface has no docstring, document it from the code behavior and flag it as needing a docstring.
- Keep the README lean — point to docs/ for details.
