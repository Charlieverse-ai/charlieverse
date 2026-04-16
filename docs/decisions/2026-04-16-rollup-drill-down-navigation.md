---
title: Dashboard rollup clicks drill down one tier instead of opening the rollup
date: 2026-04-16
status: accepted
tags: [dashboard, navigation, stories, ux, rollups]
---

# Dashboard rollup clicks drill down one tier instead of opening the rollup

## Context

The dashboard surfaces stories across tiers: session, daily, weekly, monthly. Previously, clicking a weekly story opened the weekly rollup Markdown in a reader; clicking a monthly story opened the monthly Markdown. Both behaved like any other story click — they rendered the generated rollup prose for that period.

The rollup prose is already what the AI sees. Weekly and monthly stories get loaded into activation context at session start as part of the tiered narrative compression; the model has read them by the time the user is looking at the dashboard. Re-reading the generated summary in the dashboard reader is a poor use of that screen when the raw materials (the dailies that made up the week, the weeklies that made up the month) are sitting in the store one query away.

There was also no way to see the current week before a weekly rollup existed. Dailies rolled up on Sunday; Monday through Saturday the in-progress week was invisible in the chapter timeline.

## Decision

Pivot weekly and monthly clicks one tier down, and surface the live week at the top of the dashboard.

- **Weekly click → `WeekReader`**: `AppShell.openStory` intercepts stories with `tier === 'weekly'`, opens a `WeekReader` page that queries daily stories overlapping the weekly's Monday–Sunday period via `useStoriesInPeriod('daily', ...)`, and stacks them with per-day headers.
- **Monthly click → `MonthReader`**: Same pattern one tier up. `MonthReader` lists the weekly stories for the month's period and routes each weekly entry back through the same weekly-pivot handler, so the full drill is `month → weeks → days`.
- **"This Week" block**: The dashboard computes the live Mon–Sun window with `weekBounds()` and renders the dailies for that window ahead of the chapter timeline. Those same dailies are excluded from the chapter timeline to avoid duplication.
- **Fallback to rollup content**: When the lower-tier query returns empty — common for older periods that only ever got the rollup, never the constituent pieces — the reader renders the originating rollup's Markdown. `AppShell` carries the triggering story as `fallbackStory` on the active-week / active-month state; `WeekReader` and `MonthReader` fall back to `<Markdown content={fallbackStory.content} />` when their period query returns no rows. The header picks up a `· weekly summary` / `· monthly summary` suffix so it's clear what's being shown.

Supporting plumbing:

- `/api/stories` grew `period_start` and `period_end` query params. When both are set, the handler delegates to the existing `StoryStore.find_by_period(...)` for timezone-aware overlap matching; otherwise it uses the old `fetch(tier=..., limit=...)` path.
- `useStoriesInPeriod(tier, periodStart, periodEnd)` is a new React Query hook that gates on both dates being set.
- `web/src/lib/dates.ts` gained `parseLocalDate`, `toLocalDateStr`, `weekBounds` (Monday-anchored, local-timezone-safe), and `weekRangeLabel` (e.g. "Apr 13 – Apr 19").
- Chapter weeks within each month are sorted newest-first by `period_start`, matching the rest of the dashboard's newest-at-top convention.

## Alternatives Considered

- **Keep opening the rollup, add a separate "expand" affordance**: Two affordances per card (rollup vs. drill-down) — more UI chrome, and the wrong default for the common case. The rollup is already in the model's context; the dashboard is more useful as navigation than as a re-reader.
- **Always show all three tiers side by side**: A dashboard that renders dailies and weeklies and monthlies simultaneously is noisy. The drill-down treats the tiers as layers the user can descend into on demand, with the rollup as the fallback when there's nothing to descend into.
- **Skip the fallback and show an empty state**: What the branch before the fallback did — and it left users stranded on older periods that only ever got a weekly or monthly rollup. The rollup content is the right answer in that case; the fallback makes it the answer.
- **Compute week bounds server-side**: Possible but forces every click to round-trip before the reader can render its skeleton. Doing the math in `web/src/lib/dates.ts` keeps the bounds available at click time; the server is only consulted for the story rows.

## Consequences

- The dashboard is now a navigation layer over the raw materials. Users click down into the week to see which days mattered, and into the month to see which weeks mattered.
- The current week is visible on Monday, not only after Sunday's rollup runs.
- Older periods that only have a rollup still work: the reader shows the rollup Markdown with a "summary" suffix on the header. No dead-end empty state.
- `/api/stories` has two call shapes: list-by-tier (old) and list-in-period (new). Callers must pass both `period_start` and `period_end` for the new shape; the endpoint silently falls back to tier+limit otherwise.
- All date math for week bounds is local-timezone-anchored via `parseLocalDate` and `toLocalDateStr`. Dashboards viewed near midnight boundaries won't flip weeks due to UTC shifts.
