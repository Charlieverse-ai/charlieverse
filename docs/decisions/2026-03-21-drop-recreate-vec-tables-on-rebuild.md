---
title: Drop and recreate vec tables on rebuild instead of incremental updates
date: 2026-03-21
status: accepted
tags: [search, database, embeddings, sqlite-vec]
---

# Drop and recreate vec tables on rebuild instead of incremental updates

## Context

The `rebuild_vec()` methods in `MemoryStore`, `KnowledgeStore`, and `StoryStore` originally performed incremental updates: either calling `upsert_embedding()` per row (memory and knowledge stores) or issuing a `DELETE FROM table_vec` followed by per-row inserts (story store). In practice, these approaches produced silent corruption in the vec0 virtual tables under certain conditions — partial writes could leave the index in an inconsistent state, and `DELETE` on a vec0 table does not release its allocated storage.

## Decision

Replace all incremental `rebuild_vec()` strategies with a drop-and-recreate cycle:

1. Collect all source rows and compute embeddings.
2. Resolve rowids with a SELECT before touching the vec table.
3. `DROP TABLE IF EXISTS <table>_vec`
4. `CREATE VIRTUAL TABLE <table>_vec USING vec0(embedding float[384])`
5. Bulk-insert all rows.
6. Commit.

This pattern is applied uniformly to `entities_vec`, `knowledge_vec`, and `stories_vec`.

Note: this applies to the bulk `rebuild_vec()` path only. The per-row `upsert_embedding()` path used during normal writes is unchanged. This is intentional: the incremental path is safe for single-row operations; the bulk rebuild path is where vec0 corruption was observed.

## Alternatives Considered

- **Keep incremental upserts**: The original approach. Failed silently — vec0 virtual tables can produce inconsistent state after partial writes, and the corruption is not surfaced as an error.
- **DELETE all rows then reinsert**: Used by `StoryStore` before this change. `DELETE` on vec0 does not reclaim space, so repeated rebuild cycles grow the database file unboundedly. Also still susceptible to partial-write corruption.
- **Truncate via internal vec0 shadow tables**: The vec0 extension exposes internal shadow tables but manipulating them directly is undocumented and fragile across extension versions.

## Consequences

- `rebuild_vec()` is now a safe, idempotent operation: running it any number of times leaves the vec table in a consistent, compact state.
- The database file does not grow on repeated rebuilds because `DROP TABLE` reclaims space.
- There is a brief window during rebuild where the vec table does not exist. Any concurrent search during this window will fail with a missing-table error. This is acceptable because `rebuild_vec()` is only called from the maintenance endpoint, not during normal operation.
- Future vec tables added to new stores must follow this same drop-and-recreate pattern for `rebuild_vec()`.
- The asymmetry with FTS5 (which uses per-row sync everywhere) is intentional: FTS5 tables support safe incremental operations; vec0 tables do not.
