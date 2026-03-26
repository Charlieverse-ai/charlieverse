---
title: Drop EntityType.is_workspace_scoped property
date: 2026-03-26
status: accepted
amends: 2026-03-22-project-event-entity-types-and-scoping-rules.md
tags: [memory, entities, workspace, entity-types, cleanup]
---

# Drop EntityType.is_workspace_scoped property

## Context

The `is_workspace_scoped` property was added to `EntityType` as the "canonical enforcement point" for workspace-scoping rules (see [2026-03-22 ADR](2026-03-22-project-event-entity-types-and-scoping-rules.md)). It distinguished technical types (decision, solution, milestone, project) as workspace-scoped from personal types (moment, preference, person, event) as global.

The property was never actually used to filter queries in production code — it existed only as documentation of intent and was referenced in tests. When workspace filtering was removed from session and story stores (see [2026-03-26-workspace-as-metadata-not-filter.md](2026-03-26-workspace-as-metadata-not-filter.md)), `is_workspace_scoped` became entirely dead code with no callers.

## Decision

Remove the `is_workspace_scoped` property from `EntityType`. The scoping intent it documented is now moot — workspace is metadata, and no part of the system branches on an entity type's workspace scope.

## Alternatives Considered

- **Keep it as documentation**: Leaving dead properties risks confusing future readers into thinking the scoping rules are enforced somewhere. Removing it is cleaner signal.
- **Reuse it for a different scoping mechanism**: No concrete need exists for such a mechanism now. YAGNI applies.

## Consequences

- `EntityType` is simpler — it is now a pure enum of string values with no behavior.
- Tests that asserted `is_workspace_scoped` values have been removed or rewritten to test only the string enum values.
- If workspace-aware entity filtering is ever needed in the future, the property should be reintroduced with actual call sites at that time, not speculatively.
