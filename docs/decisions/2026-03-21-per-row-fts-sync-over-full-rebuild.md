---
title: Per-row FTS sync over full-table rebuild
date: 2026-03-21
status: accepted
amends: 2026-03-14-hybrid-search-fts5-sqlite-vec.md
tags: [search, database, fts5, performance]
---

# Per-row FTS sync over full-table rebuild

## Context

This amends [2026-03-14 - Hybrid search with FTS5 + sqlite-vec](2026-03-14-hybrid-search-fts5-sqlite-vec.md).

The original FTS5 integration used `INSERT INTO table_fts(table_fts) VALUES('rebuild')` on every write operation. This performs a full table scan to rebuild the entire FTS index, which is unnecessarily expensive for single-row changes and blocks concurrent readers.

## Decision

Replace full FTS rebuilds on individual writes with per-row FTS operations using the FTS5 `delete` command and direct rowid-keyed inserts:

- **Insert**: after inserting a row into the source table, look up its `rowid` and insert directly into the FTS table with that rowid.
- **Update**: before updating a source row, delete the old FTS entry using the pre-update values; after updating, insert a new FTS entry with the updated values.
- The `rebuild_fts()` public method is retained for startup reconciliation only.

The same pattern is applied to `MemoryStore`, `KnowledgeStore`, and the hooks API work_logs/messages endpoints.

## Alternatives Considered

- **FTS5 triggers**: SQLite FTS5 external content tables support `content_rowid` for automatic sync via triggers. Rejected because aiosqlite runs on a single connection and triggers fire synchronously — mixing trigger-driven sync with async transaction management is error-prone.
- **Keep full rebuild**: Simple but O(n) on every write. Unacceptable at scale and holds a write lock during rebuild.

## Consequences

- FTS writes are now O(1) per change instead of O(n) over the full table.
- The delete-before-update pattern requires reading the old row values before the UPDATE executes — one extra SELECT per update operation.
- The startup `rebuild_fts()` reconciliation ensures any drift (e.g., from a crash mid-write) is corrected on next server start.
- Future stores must follow this pattern: insert via rowid lookup, delete via pre-update values lookup.
