---
title: Banned words moved from permanent prompt to hook-delivered reminder
date: 2026-04-16
status: accepted
tags: [prompts, reminders, hooks, voice, context-budget]
---

# Banned words moved from permanent prompt to hook-delivered reminder

## Context

Charlie's voice kill list — roughly seventy banned phrases and words like "comprehensive", "let me check", "best practices", "you're right" — was inlined into `prompts/Charlie.md` as a giant string baked into the permanent system prompt. Every turn paid the token cost of that list, even though its job is to nudge the model's word choice rather than to be freshly re-read before every response.

Permanent prompt space is the most expensive context budget. Guidance that doesn't need to be re-read every turn should live somewhere cheaper.

## Decision

Move the banned-words list out of the permanent system prompt and into the hook-reminder system:

- The canonical list lives in `charlieverse/helpers/banned_words.py` as `BANNED_WORDS` (a set) with a `banned_word_string()` helper that renders it for template substitution.
- A new `BannedWordsRule` in `charlieverse/context/reminders/rules/banned_words.py` is registered alongside the other reminder rules. It fires on `UserPromptSubmit` events and is time-gated: it re-emits at most once every `REMINDER_INTERVAL_SECONDS = 1800` (30 minutes), keyed off `seconds_since_last_save` / `seconds_since_session_start` in the hook context metadata.
- The template lives at `prompts/reminders/banned_words.md` and renders `Charlie NEVER uses the following words/phrases: ${BANNED_WORDS}`.

The voice kill list is no longer carried in `Charlie.md`'s permanent text. Higher-level voice *rules* (pattern-level guidance like "never use the didn't-just-X-it-Y escalation" and "never use stage directions") remain in `Charlie.md` since those are rules, not a word list.

## Alternatives Considered

- **Leave the list in `Charlie.md`**: Simple but costs tokens on every turn forever. The list also grows over time as new phrases are caught.
- **Ship as a first-turn system reminder only, never re-emit**: Adherence drift — the list needs periodic reinforcement during long sessions. The 30-minute cadence is a middle ground.
- **Re-emit on every `UserPromptSubmit`**: Over-injects the list and costs tokens for no additional benefit within a short burst of turns. The time gate avoids spam.
- **Generate the list dynamically from recent assistant output**: Out of scope; the list is currently maintained by hand as Charlie's voice evolves.

## Consequences

- The permanent system prompt loses roughly seventy phrases' worth of tokens per turn.
- The banned-words reminder reaches the model via the same mechanism as other hook reminders (temporal gap, save-session, search-memories) — a consistent delivery path.
- The list is maintained in one Python file (`helpers/banned_words.py`) rather than embedded in a Markdown prompt. Adding a phrase is a one-line code change.
- The 30-minute interval is a tunable constant; if adherence drifts we can shorten the cadence without changing the mechanism.
- `prompts/Charlie.md` still contains the *structural* voice rules (first-person usage, "our" vs. "your", the escalation pattern ban) because those are behavioral patterns, not strings to avoid. Only the phrase blocklist moved.
