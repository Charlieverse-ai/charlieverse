---
title: Entity list ordering changed from created_at to updated_at DESC
date: 2026-03-22
status: accepted
tags: [memory, entities, ordering, database]
---

# Entity list ordering changed from created_at to updated_at DESC

## Context

`MemoryStore.list()` ordered results by `created_at DESC`. This meant an entity that was originally created long ago but recently updated would appear at the bottom of the list, behind entities created more recently but never touched. In the context of activation, moments (memories of past interactions) are retrieved in bulk — up to 1000 — and the most relevant ones should be the most recently visited or refreshed, not the most recently created.

## Decision

Change the `ORDER BY` clause in both the filtered and unfiltered variants of `MemoryStore.list()` from `created_at DESC` to `updated_at DESC`. Updated entities surface first regardless of when they were originally created.

Tests were added to cover both the unfiltered and type-filtered list paths, verifying that an entity updated after creation appears before one that was never updated.

## Alternatives Considered

- **Add an explicit `last_accessed_at` field**: More semantically precise, but adds schema complexity. `updated_at` is already maintained and is a reasonable proxy — an entity that gets re-saved was recently relevant.
- **Keep `created_at` ordering, apply re-ranking at the application layer**: More flexible but adds code and doesn't help callers who use raw SQL results.
- **Caller-specified sort order**: Makes the interface more complex for a decision that should be a sensible default.

## Consequences

- List results now reflect recency of modification, not creation. Callers that depended on creation order will see different results.
- The context builder loads moments ordered by most recently updated — this aligns with the temporal weighting strategy in the renderer.
- The test suite now verifies ordering behavior for both list variants, preventing regression.
