---
title: Remove Work Log system (model, store, API, CLI command)
date: 2026-03-31
status: accepted
tags: [database, api, cli, architecture, work-logs]
---

# Remove Work Log system (model, store, API, CLI command)

## Context

Charlieverse originally shipped a work-log feature: a dedicated `work_logs` table, a `WorkLogStore`, REST endpoints (`POST /api/log`, `GET /api/work-logs/latest`), a `WorkLog` model, and a `charlie log` CLI command. The feature was intended to let agents record logbook entries and query the most recent one to determine the unprocessed event range.

In practice the feature was never wired into the activation context, never queried by the MCP tools, and never referenced by the skills or agent prompts. It added schema complexity, a FTS5 virtual table, and public API surface area with no active consumers.

## Decision

Remove the work-log system entirely:
- Delete `charlieverse/models/work_log.py` and the `WorkLog` model
- Delete `charlieverse/db/stores/work_log_store.py` and `WorkLogStore`
- Remove `POST /api/log` and `GET /api/work-logs/latest` REST endpoints from `hooks.py`
- Remove the `charlie log` CLI command (`cli/log_cmd.py`)
- Drop the `work_logs` and `work_logs_fts` tables from the migration schema
- Remove all exports from `__init__.py` files

## Alternatives Considered

- **Keep as dormant feature**: Retaining unused code adds cognitive overhead and creates maintenance debt when dependencies or schema change. No upside.
- **Move to a plugin**: The feature had no defined use case, so extracting it to an optional plugin would preserve the dead weight in a different form.

## Consequences

- The schema migration (`0001_init.sql`) no longer creates the `work_logs` tables. Existing databases that already ran the migration keep their tables — the removal is schema-forward only.
- The `charlie log` command is no longer available. Users who relied on it will need an alternative workflow.
- The REST API surface is smaller and the startup store initialization is lighter.
- If a log/journal feature is needed in the future, it should be redesigned around the existing entity/memory model rather than a separate table.
