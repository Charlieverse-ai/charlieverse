---
title: Vector rebuild made synchronous on server startup
date: 2026-03-31
status: accepted
tags: [server, startup, vector-search, performance, architecture]
---

# Vector rebuild made synchronous on server startup

## Context

The MCP server previously rebuilt vector indexes (memories, knowledge, stories) in a background asyncio task after the lifespan started. The task was tracked via a `track_task()` helper and cancelled during shutdown. This pattern was intended to avoid blocking server startup while embeddings were computed.

In practice, the background rebuild caused race conditions — requests arriving immediately after startup would query stale vector indexes. The `HuggingFace` and `transformers` libraries also emit noisy progress bars and warnings to stderr during model loading, which cluttered server logs.

## Decision

Replace the background rebuild task with a synchronous `await` during the lifespan startup sequence. The server now waits for all three vector index rebuilds (memories, knowledge, stories) to complete before yielding to the request handler.

Additionally, silence HuggingFace/transformers noise by setting environment variables before the rebuild:
- `HF_HUB_VERBOSITY=error`
- `TRANSFORMERS_VERBOSITY=error`
- `HF_HUB_DISABLE_PROGRESS_BARS=1`

The `track_task` helper and the background task plumbing are removed entirely.

## Alternatives Considered

- **Keep background rebuild, fix the race**: Requires adding a "ready" flag that search endpoints check before returning results — added complexity with no clear benefit given the startup latency is acceptable.
- **Lazy rebuild on first search**: Complicates the search path and produces inconsistent first-request latency. The rebuild is a one-time cost, not a per-request cost.

## Consequences

- Server startup is slower by the time required to rebuild all three vector indexes. On a typical database this is a few seconds.
- Vector search is always consistent from the first request — no stale-index window.
- The `tasks.py` `track_task` helper is no longer used by the server (though it remains in the codebase).
- `HuggingFace` output is silenced globally for the server process. This affects all HuggingFace operations, not just the rebuild.
