---
title: Project and event entity types with explicit workspace-scoping rules
date: 2026-03-22
status: accepted
tags: [memory, entities, workspace, entity-types]
---

# Project and event entity types with explicit workspace-scoping rules

## Context

The memory system's `EntityType` enum had six types: decision, solution, preference, person, milestone, moment. Two common categories of things Charlie needed to remember had no home: projects (ongoing initiatives tied to a workspace) and events (calendar-like records of things that happened or are scheduled). These were being shoehorned into moments or decisions, which muddied retrieval and made entity types semantically inaccurate.

Additionally, as the entity list grew, the workspace-scoping rule — which types are per-workspace and which are global across all workspaces — needed to be explicit rather than implicit in the match arm of `is_workspace_scoped`.

## Decision

Add `project` and `event` as first-class `EntityType` values.

Scoping rules:
- **project** is workspace-scoped (like decision, solution, milestone). A project belongs to the technical context it was created in.
- **event** is global (like person, moment, preference). Events are personal — a job interview or a life event is not tied to a coding workspace.

The `is_workspace_scoped` property on `EntityType` is the canonical enforcement point for this rule. Any new entity type must explicitly be placed in one branch of the match arm.

## Alternatives Considered

- **Use existing types**: `project` as a `decision` or `milestone`, `event` as a `moment`. These work structurally but produce wrong results at recall time — a project retrieved under "decisions" or an event under "moments" is categorically wrong and harder to filter.
- **Free-form tags instead of types**: Tags like `#project` or `#event` would avoid changing the schema. But recall is filtered by type in some queries, and tags are optional and inconsistent. A type-level distinction is reliable.
- **Separate table for events**: Overkill. Events are memories with structured content fields (what/when/who/where/why). Storing them in the entity table with a rich content string keeps the schema simple.

## Consequences

- Future entity types must explicitly declare workspace scope in the `is_workspace_scoped` match arm — the pattern is now enforced by exhaustive matching.
- `remember_project` and `remember_event` are now exposed as MCP tools. Tool descriptions must remain accurate as the primary contract for LLM callers.
- The event content format uses labeled fields (`What:`, `When:`, `Who:`, etc.) to make recall output human-readable without a custom renderer.
- The entity count comment ("The six types...") must be kept in sync whenever types are added — or removed as it was in this change.
