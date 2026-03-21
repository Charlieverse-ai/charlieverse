---
title: Story cascade falls back to raw sessions when lower-tier stories are absent
date: 2026-03-21
status: accepted
amends: 2026-03-15-tiered-narrative-compression.md
tags: [storyteller, memory, stories, cascade, sessions]
---

# Story cascade falls back to raw sessions when lower-tier stories are absent

## Context

This amends [2026-03-15 - Tiered narrative compression via Storyteller](2026-03-15-tiered-narrative-compression.md).

The original tiered compression design assumed each tier would always have source data from the tier below it. In practice this breaks down: a user might trigger a weekly rollup before any daily stories exist for that week, or a monthly rollup before enough weeklies have accumulated. The cascade in `session-save` was gated behind an opt-in `"cascade"` argument, which meant higher-tier stories silently went missing.

## Decision

`get_story_data` now queries `session_store.recent_within_range` and includes raw sessions in its response when no lower-tier stories exist for the requested period. The response includes a `"fallback": "sessions"` field to signal this path. The session-save cascade is now unconditional — weekly and monthly rollups are always attempted, not only when explicitly requested.

The Storyteller is expected to handle both response shapes: stories (with title/summary/content) and sessions (with what_happened/for_next_session).

## Alternatives Considered

- **Keep cascade opt-in, require explicit "cascade" argument**: The original approach. Simple, but in practice higher-tier stories never got generated because the skill invocation rarely included the flag.
- **Fail the rollup when no lower-tier stories exist**: Correct in theory, but in a new or sparse installation it means months before the story tiers have useful content. The fallback lets the system bootstrap from raw sessions alone.
- **Pre-generate all tiers on session-save automatically**: The chosen approach — unconditional cascade — achieves this. The fallback sessions mechanism makes it viable by ensuring `get_story_data` always returns something workable if the session data exists.

## Consequences

- Higher-tier stories now generate even on a fresh install with no existing daily/weekly stories, as long as raw sessions with `what_happened` + `for_next_session` exist for the period.
- The Storyteller must handle a heterogeneous input format — a mix of story objects and session objects in different rollup shapes.
- A new query method `recent_within_range` is introduced on `SessionStore`, scoped to sessions with complete save data (both fields present, not soft-deleted).
- Cascade runs on every session save. For heavy users this adds latency to the save flow. The trade-off is accepted because story generation is async and the tiers are idempotent.
