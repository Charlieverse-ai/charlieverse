---
title: Raw sessions as activation fallback over derived stories
date: 2026-03-19
status: accepted
tags: [activation, context, reliability, sessions]
---

# Raw sessions as activation fallback over derived stories

## Context

The activation context originally loaded session-tier stories as the primary data source for recent session history. This created a single point of failure — if the Storyteller didn't run (skill wasn't triggered, agent errored, session ended abruptly), the session data was invisible in the next activation. Missing one Storyteller run meant a gap in Charlie's memory of what happened.

## Decision

Load raw sessions from the last 2 days directly via `recent_within_days()` on the SessionStore. Show `what_happened` and `for_next_session` fields directly in the activation context. Stories still exist and are loaded for broader timeframes (weekly, monthly, all-time), but raw sessions are the source of truth for recent history.

## Alternatives Considered

- **Make Storyteller more reliable**: Doesn't fix the architectural problem. Any system that depends on a derived artifact being generated is fragile by design.
- **Queue failed story generations for retry**: Adds complexity (retry logic, dead letter handling) to solve a problem that raw data access eliminates.
- **Store raw session data in stories table**: Muddies the boundary between raw data and compressed narratives.

## Consequences

- Activation context always has recent session data, regardless of whether the Storyteller ran.
- Slightly higher token usage for recent history (raw fields vs compressed story), but bounded to 2 days.
- Stories become enrichment, not infrastructure. If story generation breaks, Charlie still knows what happened yesterday.
- The `for_next_session` field in raw sessions acts as a direct handoff between sessions — no interpretation layer.
