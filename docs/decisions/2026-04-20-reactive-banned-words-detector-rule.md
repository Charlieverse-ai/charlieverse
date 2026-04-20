---
title: Reactive Banned-Words Detector Added as Separate Reminder Rule
date: 2026-04-20
status: accepted
tags: [banned-words, reminders, voice, architecture]
---

# Reactive Banned-Words Detector Added as Separate Reminder Rule

## Context

The existing `BannedWordsRule` fires a static reminder listing all banned phrases on every prompt. It's a proactive nudge. There was no mechanism to catch the case where Charlie had already used a banned phrase in the previous turn and needed immediate corrective feedback.

The existing rule relies on the last assistant message being available in the hook context (`PromptSubmitContext.last_assistant_message`), which was added specifically to enable reactive detection.

## Decision

Add `BannedWordsDetectorRule` (`banned_words_detector.py`) as a separate rule that fires with `ReminderTag.VERY_IMPORTANT` priority when the previous assistant message contains a banned phrase. It calls `check_text()` on the last assistant message and renders a `banned-words-violation` template with the specific matches.

The rule is registered after `SearchMemoriesRule` and before `BannedWordsRule` so reactive violations appear before the general reminder list.

## Alternatives Considered

- **Merge into `BannedWordsRule`**: Would conflate proactive and reactive concerns in one class and make testing harder.
- **Post-processing hook on assistant responses**: Would require a different hook event type; the existing `UserPromptSubmit` path already has the previous assistant message available.

## Consequences

- Charlie gets immediate, specific feedback when it has just used a banned phrase, not just a general reminder of what's banned.
- The `last_assistant_message` field on `PromptSubmitContext` is now load-bearing for this rule — it must be populated by the prompt-submit hook.
- `VERY_IMPORTANT` tag ensures the violation surfaces prominently in the reminder injection.
