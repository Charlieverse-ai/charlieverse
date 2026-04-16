---
title: Scoped ty overrides for httpx lazy imports instead of inline suppressions
date: 2026-04-16
status: accepted
tags: [ty, typing, httpx, tooling, suppressions]
---

# Scoped ty overrides for httpx lazy imports instead of inline suppressions

## Context

Four files import `httpx` lazily inside async functions so the import cost isn't paid on CLI startup or on reminder-rule registration:

- `charlieverse/cli/context_cmd.py`
- `charlieverse/cli/hooks_cmd.py`
- `charlieverse/cli/story_data_cmd.py`
- `charlieverse/context/reminders/rules/search_memories.py`

Each uses `httpx.AsyncClient`, `httpx.ConnectError`, and `httpx.HTTPError`. These are attributes that `httpx` re-exports from its internal modules, and ty's current stub discovery doesn't resolve them — every access raises `unresolved-attribute`, even though the attributes are present at runtime (verified against `httpx 0.28.1`).

The earlier fix (v1.14.3) silenced the warnings with per-line `# ty:ignore[unresolved-attribute]` comments at each call site. Emily then removed those comments in `a961c2a` on the preference that code shouldn't carry inline suppressions. That left the four files failing ty with genuine-looking errors that weren't actually bugs, and `unresolved-attribute` broken as a useful signal — real missing-attribute bugs anywhere in the codebase would be drowned out by the known-false httpx noise.

## Decision

Add a scoped override block in `pyproject.toml` that disables `unresolved-attribute` for exactly those four files:

```toml
[[tool.ty.overrides]]
include = [
    "charlieverse/cli/context_cmd.py",
    "charlieverse/cli/hooks_cmd.py",
    "charlieverse/cli/story_data_cmd.py",
    "charlieverse/context/reminders/rules/search_memories.py",
]

[tool.ty.overrides.rules]
unresolved-attribute = "ignore"
```

The override sits directly after `[tool.ty.src]` and is commented with the reason (httpx stub discovery) so the next person to read it knows why the scope exists. The rule stays active for every other file in `charlieverse/` and `tests/`.

## Alternatives Considered

- **Keep the per-line `# ty:ignore[unresolved-attribute]` suppressions**: Works, but noisy at each call site and Emily has said she doesn't want inline suppressions in the code. The file-scoped override keeps the suppression out of the source files entirely.
- **Disable `unresolved-attribute` globally**: One line change, but it turns off a rule that catches real bugs everywhere else. The whole reason to bother with a scoped override is to keep the rule useful for the rest of the codebase.
- **Move the httpx imports to module top level so ty sees them eagerly**: Breaks the reason the imports are lazy in the first place — CLI startup cost and reminder-rule registration cost. The laziness is load-bearing.
- **Switch to a different HTTP client with better ty support**: Disproportionate — replace a working dependency because of a stub-discovery quirk in one type checker.
- **Wait for ty to grow better httpx stub discovery**: Fine as an eventual path, but the ty pass needs to be green in the meantime; nothing prevents removing the override once upstream catches up.

## Consequences

- `ty` passes clean on the four files without any in-source suppression comments.
- `unresolved-attribute` remains an active rule for every other file in the codebase; a genuine typo or missing attribute elsewhere will still be caught.
- The override has a narrow blast radius by path, so a future file that also imports httpx lazily would need to be added to the `include` list explicitly. This is the intended behavior — it forces a conscious decision each time the suppression expands.
- The reason for the override lives in the `pyproject.toml` comment above the block rather than scattered at call sites. One place to revisit when ty's stub discovery improves or when httpx changes its re-export pattern.
- If the override is ever removed, the four files will need either restored inline suppressions or a different fix — it's worth re-checking httpx stub behavior before the next removal attempt.
