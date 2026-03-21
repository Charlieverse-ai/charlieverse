---
title: ToolError and StoreContext as MCP tool conventions
date: 2026-03-20
status: accepted
tags: [mcp, tools, error-handling, typing]
---

# ToolError and StoreContext as MCP tool conventions

## Context

The MCP tool layer accumulated two recurring problems: invalid inputs (empty required strings) produced opaque internal errors that surfaced as unhelpful messages to LLM clients, and the lifespan `dict` carrying the store and vec rebuild task was untyped, causing `unresolved-attribute` diagnostics throughout server.py and tools files.

## Decision

Two conventions are now established for all MCP tools:

1. **ToolError for input validation**: Every `@mcp.tool` function validates required string parameters at entry and raises `ToolError` (not `ValueError`, not a `{"error": ...}` dict return) for empty or missing inputs. This surfaces structured errors to the LLM client rather than leaking implementation details.

2. **StoreContext TypedDict**: A `StoreContext` TypedDict in `charlieverse/mcp/context.py` defines the shape of the lifespan dict — containing `store` and optionally the background `vec_task` handle. All tool functions access context via this type. The background task is cancelled in the lifespan `finally` block to prevent leaks on shutdown.

## Alternatives Considered

- **Silent `{"error": ...}` dict returns**: Already in use before this change. Inconsistent (some tools raised, some returned), and the dict format is invisible to clients that expect either a result or an exception.
- **Untyped `dict` lifespan context**: Zero-friction initially but produced three persistent type errors and made it unclear what the context was expected to contain.
- **Per-tool context access pattern without a shared type**: Each tool could cast independently. Creates divergence and doesn't eliminate the diagnostics.

## Consequences

- New MCP tools must raise `ToolError` for validation failures, not return error dicts or raise generic exceptions.
- The lifespan context must be accessed via `StoreContext` — add new fields there when the lifespan needs to carry additional state.
- `ToolError` is the MCP-idiomatic way to communicate tool-level failures to clients; it appears as a structured error in the tool call result rather than crashing the server.
- The background vec rebuild task handle must be stored on context so the lifespan cleanup can cancel it — fire-and-forget asyncio tasks are not acceptable in the server.
