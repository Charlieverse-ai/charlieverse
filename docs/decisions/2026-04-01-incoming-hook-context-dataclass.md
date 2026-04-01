---
title: Centralize Hook Stdin Parsing with IncomingHookContext Dataclass
date: 2026-04-01
status: accepted
tags: [hooks, refactoring, architecture]
---

# Centralize Hook Stdin Parsing with IncomingHookContext Dataclass

## Context

Hook commands (`session-start`, `prompt-submit`, `stop`, `tool-use`, `session-end`) all receive provider input via stdin as a JSON blob. Before this change, each hook command independently parsed stdin, extracted `session_id` and `cwd`, checked for subagent context, and handled missing or malformed fields in its own way. The logic was duplicated and inconsistent across commands — some used `uuid4()` fallbacks when `session_id` was missing, others silently skipped, and validation behavior varied.

A new agent-type guard was also needed: hooks should only fire for `Charlieverse:Charlie` agents, not arbitrary subagents spawned by other tools. Adding this consistently would have required touching every hook command individually.

## Decision

Extract all stdin parsing, validation, and early-exit logic into a single `_incoming_context()` helper that returns an `IncomingHookContext` dataclass (or `None` if the hook should be skipped). Each hook command calls this helper and guards on the result with `if context:`.

The dataclass carries `event`, `session_id`, `workspace`, and `stdin` — the complete parsed context a hook needs. UUID validation is delegated to the shared `_parse_uuid` helper from `charlieverse.api.entities`.

Hooks that receive `None` from `_incoming_context()` do nothing and exit cleanly.

## Alternatives Considered

- **Per-command validation (status quo):** Already causing drift between commands and would require repeating the agent-type guard in every handler. Rejected.
- **Middleware / decorator pattern:** Would require more abstraction than the problem warrants. The hooks are simple CLI entry points, not a framework. Rejected in favor of a plain helper function.

## Consequences

- All hook stdin parsing is in one place — the agent-type guard, subagent check, UUID validation, and missing-field logging are all centralized.
- Hook commands no longer generate random UUIDs as fallback session IDs; a missing or invalid session_id is now a hard skip with a log entry, preventing phantom sessions.
- New hooks added in the future automatically get all validation by calling `_incoming_context()`.
- The `uuid4` import is removed from hooks_cmd; UUID generation at session creation stays server-side only.
