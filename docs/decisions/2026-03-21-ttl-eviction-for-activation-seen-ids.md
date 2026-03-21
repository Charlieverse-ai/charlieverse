---
title: TTL-based eviction for activation seen IDs map
date: 2026-03-21
status: accepted
tags: [server, memory-management, sessions]
---

# TTL-based eviction for activation seen IDs map

## Context

The server maintains a `_activation_seen_ids` dict mapping session IDs to the set of entity/knowledge IDs delivered at session activation. This prevents the same content from being surfaced repeatedly within a session. The original implementation was a plain `dict[str, set[str]]` with no eviction — entries accumulated indefinitely for the lifetime of the server process.

## Decision

Add TTL-based eviction with a 24-hour window. Each entry is stored as a `(set[str], float)` tuple where the float is a `time.monotonic()` timestamp. Stale entries are evicted lazily on `get_seen_ids()` access. The threshold is 24 hours (`_SEEN_IDS_TTL = 86400`).

The `get_seen_ids()` / `set_seen_ids()` accessor functions encapsulate the eviction logic, keeping the dict an implementation detail of `server.py`.

## Alternatives Considered

- **LRU cache with max size**: Would bound memory by entry count rather than time. Rejected because sessions should expire by age, not by recency — a session from 5 hours ago should still be valid even if 1000 other sessions happened since.
- **No eviction (status quo)**: Simple but causes unbounded memory growth on long-running servers. Unacceptable for a production deployment.
- **Scheduled background task**: A background asyncio task could sweep expired entries on a timer. Adds complexity without benefit — lazy eviction on access is sufficient since the dict is accessed frequently.

## Consequences

- Memory for `_activation_seen_ids` is now bounded: at most one entry per session active within the last 24 hours.
- Eviction is lazy (triggered on read), not proactive. In a scenario with many writes and no reads, stale entries persist until the next read. This is acceptable for the use case.
- `hooks.py` now uses the accessor functions instead of directly mutating the dict, which required a lazy import to resolve the `hooks → server → hooks` circular import.
