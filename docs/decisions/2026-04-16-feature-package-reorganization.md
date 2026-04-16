---
title: Reorganize charlieverse into feature packages
date: 2026-04-16
status: accepted
tags: [architecture, refactoring, packaging, modules]
---

# Reorganize charlieverse into feature packages

## Context

The package was organized by layer: a flat `charlieverse/api/`, `charlieverse/models/`, `charlieverse/db/stores/`, `charlieverse/mcp/tools_*`, and `charlieverse/tools/` each held files for every feature (entities, knowledge, sessions, stories, messages). Touching a single feature meant jumping across four or five directories — the entity model lived in `models/entity.py`, its persistence in `db/stores/memory_store.py`, its MCP surface in `mcp/tools_memory.py`, and its REST handler in `api/entities.py`. Shared helpers (`paths.py`, `skills.py`, `tasks.py`) sat at the package root next to unrelated top-level modules. Type aliases and branded types had no home at all.

This layout made it harder than it should have been to see what belonged to a feature, and easier than it should have been for features to leak into each other's internals.

## Decision

Collapse the layered layout into colocated feature packages under `charlieverse/memory/`. Each feature owns a directory with the same three files:

- `models.py` — Pydantic models and IDs
- `store.py` — persistence against SQLite
- `mcp.py` — MCP tool handlers

The features are `entities`, `knowledge`, `sessions`, `stories`, and `messages`. A small `charlieverse/memory/stores.py` aggregates the per-feature stores into a single `Stores` handle.

Three sibling reorganizations happen at the same time:

- **REST handlers** move from `charlieverse/api/` to `charlieverse/server/api/` alongside the typed response classes in `charlieverse/server/responses/` and middleware in `charlieverse/server/middleware/`. The old `charlieverse/server.py` and `charlieverse/mcp/` entry points are replaced by `charlieverse/server/start.py`.
- **Shared helpers** (`paths`, `tasks`, `skills`, `time_utils`, `banned_words`, `stop_words`) consolidate under `charlieverse/helpers/`.
- **Type-only symbols** (`NonEmptyString`, `WorkspaceFilePath`, `TagList`, `ModelId`, date helpers) move under `charlieverse/types/`.

The public surface (CLI entry points, MCP tool names, REST routes) does not change. This is pure internal shape.

## Alternatives Considered

- **Keep the layered layout, rename things for clarity**: Cosmetic fix only. Cross-directory navigation stays the same and the "where does X live" question keeps costing time on every feature change.
- **One file per feature**: `entities.py` with models + store + MCP all in one module. Works for small features but `entities.py` would already be ~1000 lines. Splitting into `models.py` / `store.py` / `mcp.py` keeps each file scannable.
- **Group by lifecycle (read-only vs. write, sync vs. async)**: Doesn't match how the code is actually touched. Features are the unit of change, not lifecycles.

## Consequences

- Adding a feature means creating one directory with a predictable shape, not six scattered files.
- Cross-feature imports are easier to notice and audit — they stand out as `from charlieverse.memory.other_feature` instead of being invisible in a shared `models/` namespace.
- The `Stores` aggregate gives handlers a single injection point instead of threading four stores through constructors.
- The diff that ships this refactor is large (187 files touched, ~7k inserted / ~7k deleted), but every move is mechanical; there is no behavior change to review.
- Future refactors within a feature only touch that feature's directory — no more ripple edits across the layered layout.
