---
title: Tiered narrative compression via Storyteller
date: 2026-03-15
status: accepted
tags: [storyteller, memory, context, architecture]
---

# Tiered narrative compression via Storyteller

## Context

Raw session data accumulates fast — hundreds of sessions, each with detailed what_happened/for_next_session fields. Loading all of this into an activation context would blow any token budget. But losing the detail means losing continuity. The system needs a way to compress history at different granularities while preserving emotional signal and decision context.

## Decision

Implement a tiered story system where raw sessions are compressed into progressively broader narratives: session → daily → weekly → monthly → all-time. Each tier reads from the tier below it. The Storyteller agent (a subagent) does the compression, following brain-friendly-stories and anti-ai-language rules. Stories are immutable once written — higher tiers synthesize from lower tiers, never modify them.

## Alternatives Considered

- **Keep all raw sessions**: Doesn't scale. Token budget exceeded within weeks of regular use.
- **Sliding window of recent sessions**: Loses long-term context. Things that happened a month ago become invisible.
- **Automated summarization without tiers**: Single-level compression loses the ability to zoom in/out. A monthly summary can't contain daily-level detail, but sometimes you need that detail.
- **Keyword extraction / tagging only**: Loses the narrative thread. Tags tell you topics, not arcs.

## Consequences

- Activation context can load the all-time story + recent weekly + raw sessions from last 2 days. Covers the full arc in ~2k tokens.
- Detail scales with recency — today is granular, last month is thematic, six months ago is a paragraph.
- Storyteller quality matters — bad compression loses signal. Brain-friendly-stories rules and peer review (Storyteller spawns a second Storyteller to fact-check) mitigate this.
- Stories are write-once. If the Storyteller produces a bad story, the fix is a new story at the same tier, not editing the original.
- The system depends on someone triggering story generation (currently via session-save skill or scheduled reminders). If stories aren't generated, the raw sessions still work as fallback.
