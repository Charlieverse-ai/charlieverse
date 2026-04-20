---
title: Save Session Reminder Switched to Escalating Turn-Based Nag
date: 2026-04-20
status: accepted
amends: (none)
tags: [reminders, save-session, ux, escalation]
---

# Save Session Reminder Switched to Escalating Turn-Based Nag

## Context

The previous save-session reminder fired once every 30 minutes based on wall-clock time (`SAVE_INTERVAL_SECONDS = 1800`). This had two problems: it could fire during inactive sessions (no messages exchanged), and it gave no sense of urgency — a single reminder was easy to ignore indefinitely.

The goal is for Charlie to save the session reliably after meaningful work has been done. A flat time-based trigger doesn't correlate with session activity at all.

## Decision

Replace the time-based trigger with a turn-based one: the reminder fires after `REMINDER_TRIGGER = 15` turns since the last save, and escalates in tone each turn thereafter. The escalation ranges from a polite nudge at turn 0 through snarky dog-explosion humor through a tombstone epitaph at turn 14.

A per-session in-memory tracker (`_last_fired_turn`) prevents the same turn count from re-firing (e.g. when two user prompts arrive before an assistant reply). The tracker resets when `turns_since_save` drops (save happened), which also triggers a one-time celebration message.

## Alternatives Considered

- **Keep time-based trigger, lower interval**: Would still fire during idle sessions and doesn't convey urgency through escalation.
- **Single reminder, no escalation**: Easier to ignore; Charlie needs to self-nag if the reminder is dismissed.
- **Escalation by total session length**: Turn count since last save is a better proxy for how much work is at risk.

## Consequences

- Save reminders are now tied to conversation activity, not the clock.
- The escalating copy keeps Charlie aware of the problem even when distracted.
- The in-process dict means escalation state doesn't survive a server restart, which is acceptable — session restarts reset the risk.
- Future code must use `PromptSubmitReminder` base class (which gates on `UserPromptSubmit` events) for this rule to fire correctly.
