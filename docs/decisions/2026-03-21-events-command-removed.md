---
title: Remove events CLI command and hook events API endpoint
date: 2026-03-21
status: accepted
tags: [cli, api, events, hooks, maintenance]
---

# Remove events CLI command and hook events API endpoint

## Context

The `charlie events` CLI command and the `POST /api/hooks/events` endpoint were added as debug/introspection surfaces for hook events — a way to query recent raw hook invocations. Over time, sessions and stories became the canonical record of what happened; the raw events endpoint duplicated that read surface without adding meaningful information that wasn't already available through session context and logs.

The endpoint was listed in API docs but had no consumers in the web dashboard and no callers in any skill or integration file. Keeping it meant maintaining surface area, testing coverage, and documentation for a feature nobody used.

## Decision

Remove the `events` subcommand from the CLI and remove the `/api/hooks/events` endpoint entirely. The `events_cmd` module is no longer registered in `cli/main.py`. The API docs entry is removed.

## Alternatives Considered

- **Keep the endpoint, mark it deprecated**: Adds noise to the API surface without benefit. Deprecated endpoints still need to be maintained.
- **Move events to a debug-only flag**: Adds complexity to the CLI startup path. The use case (low-level hook introspection) is already served by log files.
- **Replace with a structured events log**: Could be useful, but the existing session save mechanism captures the same signal at a higher level of abstraction. Building a parallel events store would duplicate work.

## Consequences

- Any external tooling calling `POST /api/hooks/events` will break. This is accepted — the endpoint was undocumented outside this codebase.
- CLI surface is smaller. `charlie --help` output no longer includes `events`.
- Raw hook event data is only available via server logs. For debugging, this is sufficient.
