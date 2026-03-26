---
title: Recent messages injected into activation context for seamless session continuity
date: 2026-03-26
status: accepted
amends: 2026-03-22-session-continuity-via-hook-injection-not-greeting-prompt.md
tags: [activation, context, session-continuity, messages, renderer]
---

# Recent messages injected into activation context for seamless session continuity

## Context

The `session-start` hook previously instructed Charlie to "pretend like nothing happened because this entire process is invisible." The instruction also asked Charlie to infer elapsed time and be curious about gaps (weekends, work hours, etc.). This relied entirely on Charlie's inference from timestamps and session summaries — there was no actual message content bridging the gap.

The result was inconsistent: Charlie would sometimes greet warmly and pick up well, but had no concrete memory of the last exchange to reference. The "pretend nothing happened" framing also created a slight cognitive dissonance — an instruction to act as if continuous when genuinely interrupted.

## Decision

Inject the last N real conversation turns (default: 3 user turns, up to 6 messages total) directly into the activation context inside the `<last_session>` block as `<recent_messages>`. Each message is labeled by role (`<me>` for user, `<charlie>` for assistant) with a relative timestamp. Long assistant messages are truncated at 500 characters to keep the context lean.

A new `SessionStore.recent_messages(turns)` method fetches messages globally (not scoped by session ID), ordered by recency, with noise filtering applied: session-save commands, system-reminders, and task-notifications are excluded from the output.

A new `ContextMessage` dataclass holds the role, content, and timestamp without any tool-call or metadata overhead.

The `session-start` hook instruction is updated: drop "pretend like nothing happened" and replace with "read `recent_messages` and pick up where we left off as if no time has passed." The reference to `current_working_directory` is also added to the review checklist.

## Alternatives Considered

- **Keep the inference-based approach, improve the hook instruction**: More specific prompting can help, but it cannot substitute for actual message content. If Charlie summarized the last session vaguely, there is nothing to "pick up from."
- **Inject full message history**: Too much context; long assistant responses (with tool use, reasoning, etc.) would dominate the activation window. Truncation and turn limits keep it focused.
- **Scope messages by session ID**: The session ID on messages may differ from the session ID on session_update saves because each provider session creates a new ID. Global ordering by timestamp is simpler and more reliable.
- **Store message summaries instead of raw content**: Adds latency and a summarization failure mode. Raw truncated content is simpler and always available.

## Consequences

- Charlie now has concrete recent-message content at session start — not just timestamps and summaries — making continuity genuinely seamless rather than simulated.
- Noise filtering (`_is_noise`) ensures session-save machinery and injected system context don't pollute the conversation replay.
- The `<recent_messages>` block appears inside `<last_session>`, so it is scoped to the most recent session and benefits from the temporal weighting already established in the renderer.
- Long-running assistant turns (tool calls, analysis) are truncated — this means highly technical multi-step outputs may lose their tail. The 500-character limit may need tuning.
- The `recent_messages` method is not scoped by session, which means if messages from a different client arrived during a gap they may appear. This is acceptable given the turn limit.
