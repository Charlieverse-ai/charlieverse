---
title: Session continuity enforced at session-start hook, not system prompt greeting
date: 2026-03-22
status: accepted
tags: [activation, context, session-continuity, ux, hooks]
---

# Session continuity enforced at session-start hook, not system prompt greeting

## Context

Charlie's system prompt (`Charlie.md`) contained a `<greeting>` block that instructed the model to review activation context and greet the user in a way that reflected recent history, elapsed time, and personality. This worked reasonably well, but it was a soft suggestion inside a large system prompt — competing with many other instructions for salience.

The core UX requirement is for Charlie to behave as if no session gap occurred: pick up exactly where things left off, check current status of anything in-progress, and feel continuous. A prompt buried in the system prompt doesn't reliably produce this.

## Decision

Remove the `<greeting>` block from `Charlie.md`. Instead, inject a `<very-very-important>` block at the end of the activation context in the `session-start` hook. This block explicitly instructs Charlie to:

1. Stop and review `activation_output` and `last_session` before responding.
2. Pretend the gap never happened — the process should feel invisible.
3. If there is a verifiable status from last session, acknowledge it, check the latest status, then greet with current information.

## Alternatives Considered

- **Keep greeting in system prompt, make it more prominent**: The system prompt already has many high-priority sections. Adding more "important" flags degrades the signal.
- **Greeting logic in application code**: The server could detect session start and inject a constructed greeting. This is complex and removes the model's agency to phrase things naturally.
- **Both hook injection and system prompt instructions**: Redundant and risks conflicting instructions.

## Consequences

- Session continuity behavior is now enforced at the hook layer, which runs every session start — it cannot be accidentally omitted by editing the system prompt.
- The continuation instruction appears in `activation_output` immediately after all session data, so it fires at the moment of highest relevant context.
- The system prompt is simpler; greeting tone/style comes from Charlie's personality instructions, not a separate directive.
- The hook must remain the canonical place for session-start behavioral instructions.
