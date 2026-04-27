---
title: Drop Moments from Activation Context
date: 2026-04-27
status: accepted
tags: [activation-context, moments, context-builder, performance]
---

# Drop Moments from Activation Context

## Context

Moments (personality/relationship memories) were fetched on every session-start and injected into the activation context alongside pinned entities, session entities, and related entities. The fetch was up to 50 moments, re-ranked by relevance and recency. In practice this was adding meaningful token overhead to every activation context, and the signal-to-noise ratio degraded as the moments store grew — older, lower-signal moments were surfacing alongside the high-value ones.

## Decision

Comment out the moments fetch in `ActivationBuilder.build()` and pass an empty list to `ContextBundle.moments`. Moments are still stored in the database and accessible via recall; they simply no longer auto-load into every activation context.

## Alternatives Considered

- **Keep moments but reduce the limit** (e.g., 10 → 5): Still adds noise from lower-signal entries; doesn't solve the core problem that moments aren't always relevant to the current session.
- **Score moments against session topic and include only high-scoring ones**: More correct but significantly more complex; deferred until there's evidence it matters.
- **Move moments into the pinned track**: Conflates two different concerns (moment = happened once, pinned = always relevant). The pinned tag already serves the "always load" use case.

## Consequences

- Activation context is leaner on every session-start.
- Moments that were previously auto-surfaced now require explicit recall or pinning to appear.
- High-value moments should be pinned — the pinning guidance in `prompts/Charlie.md` now emphasizes this.
- The moments store remains intact; the code path is commented out, not deleted, to make it easy to restore or replace with a smarter fetch strategy.
