---
title: Weekly stories removed from activation context
date: 2026-03-22
status: accepted
amends: 2026-03-19-raw-sessions-over-derived-stories.md
tags: [activation, context, stories, sessions]
---

# Weekly stories removed from activation context

## Context

The activation context renderer loaded two sources of recent history: raw sessions (from the last 2 days, established in [2026-03-19 - Raw sessions as activation fallback over derived stories](../decisions/2026-03-19-raw-sessions-over-derived-stories.md)) and weekly stories rendered as `<week_story>` blocks for periods before today. The original intent was that weekly stories would provide compressed history for the days beyond the 2-day raw session window.

In practice, weekly stories add noise: they are a derivative artifact that may lag or be absent, they occupy token budget that raw sessions could fill, and the 2-day window of raw sessions already covers the most operationally relevant history. The existing ADR noted "stories become enrichment, not infrastructure" — the weekly story blocks in activation were acting as infrastructure.

## Decision

Remove the weekly stories rendering block from the context renderer entirely. Activation context now contains only raw sessions. Stories remain in the database and continue to be generated, but they are no longer injected into the activation payload.

## Alternatives Considered

- **Keep weekly stories, make them optional/gated**: Add a flag to suppress them. Adds complexity without clear benefit — the use case for weekly stories in activation hasn't materialized.
- **Expand the raw session window beyond 2 days**: More raw data instead of compressed stories. This is a reasonable future option but isn't needed now; the 2-day window covers typical cadence.
- **Move weekly stories to a separate, on-demand tool**: Charlie could `recall` story content when explicitly needed. This is the better long-term model — stories are available but not automatically injected.

## Consequences

- Activation context is leaner and entirely composed of raw, authoritative data.
- Any session older than 2 days is not surfaced automatically at session start. This is acceptable for the current usage pattern.
- The `bundle.weekly_stories` field on `ContextBundle` is no longer rendered — it may be removed from the bundle in a follow-up if it serves no other purpose.
- Weekly story generation should continue so the data is available for on-demand queries; this decision affects rendering, not generation.
