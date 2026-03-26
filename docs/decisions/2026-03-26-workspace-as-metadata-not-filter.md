---
title: Workspace stored as metadata, not used as a query filter
date: 2026-03-26
status: accepted
amends: 2026-03-22-project-event-entity-types-and-scoping-rules.md
tags: [workspace, sessions, stories, query, memory]
---

# Workspace stored as metadata, not used as a query filter

## Context

Session and story queries previously supported an optional `workspace` parameter that filtered results to entries matching that workspace (plus global entries with a NULL workspace). The intent was to keep context focused when working in a specific project directory.

In practice this created more problems than it solved: sessions and stories from other workspaces were hidden even when they contained relevant context. A decision made in `/project/a` is often directly relevant when working in `/project/b`, especially for cross-cutting concerns. The filtering also made the system harder to reason about — whether a session appeared in context depended on which directory Charlie was started from.

## Decision

Remove workspace filtering from all session and story queries. The `workspace` column is kept in both tables as metadata (for display, organization, and potential future use), but it is no longer used as a predicate in `WHERE` clauses. All queries return results across all workspaces.

Affected methods:
- `SessionStore.recent()`
- `SessionStore.recent_within_days()`
- `SessionStore.recent_within_range()`
- `StoryStore.find_by_period()`

The `workspace` parameter is retained on each method signature for backwards compatibility but is now a no-op.

## Alternatives Considered

- **Keep filtering as opt-in**: Make filtering the exception rather than the default. Rejected — the added complexity wasn't justified when the benefit of filtering is dubious.
- **Filter at the context-builder layer**: Move filtering out of the store and into the context renderer. Rejected — this would still suppress relevant cross-workspace context without a clear benefit.
- **Remove the `workspace` column entirely**: Too destructive. Workspace remains useful metadata for understanding where a session happened, and removing it would break the data model and any tooling that displays it.

## Consequences

- Activation context is now richer — sessions and stories from all workspaces appear, weighted by recency.
- The `workspace` parameter on store methods is now a no-op; callers passing it will not get an error but will not get filtered results either.
- Tests that asserted workspace filtering behavior have been updated to assert the inverse: that multiple workspaces appear together in results.
- Future workspace-aware filtering, if ever needed, belongs at a higher layer (context renderer or API) not in the store.
