---
title: relative_time_seconds Returns Fractional Units Instead of Compound Strings
date: 2026-04-20
status: accepted
tags: [time-utils, formatting, helpers]
---

# relative_time_seconds Returns Fractional Units Instead of Compound Strings

## Context

`relative_time_seconds` previously returned compound strings like "2 hours, 35 minutes". This format is verbose in reminder injections and doesn't match how Charlie is expected to speak about durations.

The function is used in reminder rendering where concise output is preferred — "2.5 hours" reads better than "2 hours, 30 minutes" in a compact reminder context.

## Decision

`relative_time_seconds` now returns a single fractional unit: the largest unit where the value is >= 1, rendered to at most two decimal places with trailing zeros stripped. `1.0` → `"1 minute"`, `1.5` → `"1.5 minutes"`, `6.01` → `"6.01 hours"`. Pluralization is based on the rounded value (exactly 1 → singular).

A private `_fmt_unit` helper handles the rounding, formatting, and pluralization. The function now accepts `float | Seconds` rather than just `int`.

## Alternatives Considered

- **Keep compound format**: Verbose for reminders; inconsistent with how Charlie talks.
- **Round to nearest unit**: Loses precision; "2 hours" for 1h50m is misleading.
- **ISO 8601 duration format**: Machine-readable but not human-readable in a reminder.

## Consequences

- Any callers expecting "X hours, Y minutes" format will get "X.Y hours" instead. The only known call site is the `save-reminder` template which is now replaced by `annoy-charlie`.
- Fractional representation works well for the 1–24 hour range but reads oddly for very large values (e.g. "120 minutes" instead of "2 hours") — this is mitigated because the function picks the largest applicable unit.
- Test suite updated to match new expected format.
