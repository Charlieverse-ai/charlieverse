---
name: qc
description: Run quality control checks on the codebase — type checking, linting, tests, and server smoke test. Use when the user says "/qc", wants to verify code quality, or after making significant changes.
argument-hint: '[scope: all|types|tests|smoke (default: all)]'
---

## What this skill does

Runs a multi-stage quality control pipeline: type checking, linting, unit tests, and a live server smoke test. Reports pass/fail for each stage with details on failures.

## Steps

### 1. Type checking

```bash
uv run ty check
```

Report the number of diagnostics. Zero is the target — any failures should be listed with file and line.

### 2. Tests

```bash
uv run pytest tests/ -v --tb=short 2>&1
```

Report pass/fail counts. If tests don't exist yet, note that and skip (don't fail QC for missing tests during early development).

### 3. Server smoke test

Start the server if it's not already running:

```bash
charlie server status
```

If not running, start it:

```bash
charlie server start
```

Wait for health:

```bash
curl -s http://localhost:8765/api/health
```

Then verify REST endpoints respond with valid JSON:

```bash
curl -s http://localhost:8765/api/entities | head -c 200
curl -s http://localhost:8765/api/knowledge | head -c 200
curl -s http://localhost:8765/api/stories | head -c 200
```

Check all return JSON (arrays or objects, not HTML or errors).

Then verify MCP tools work by calling recall through the CLI:

```bash
charlie hooks session-start 2>&1 | head -c 500
```

Check that activation context is generated (contains XML tags or markdown). This exercises the full MCP → store → context pipeline.

### 4. Web dashboard check

```bash
curl -s http://localhost:8765/ | grep -c '<div id="root">'
```

Verify the SPA index.html is served.

### 5. Report

Summarize results:

| Check | Status |
|-------|--------|
| Type checking | X diagnostics |
| Tests | X passed, X failed |
| Server health | OK/FAIL |
| MCP tools | OK/FAIL |
| REST API | OK/FAIL |
| Web dashboard | OK/FAIL |

If any stage fails, list the specific failures with enough detail to fix them.

### Scope options

If `$ARGUMENTS` specifies a scope:

- `types` — only run type checking
- `tests` — only run tests
- `smoke` — only run server smoke test
- `all` (default) — run everything
