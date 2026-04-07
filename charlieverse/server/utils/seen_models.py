"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import time

from charlieverse.memory.sessions import SessionId
from charlieverse.types.id import ModelId

# session_id -> (IDs delivered at activation, timestamp).
# Entries older than 24h are evicted on access to prevent unbounded growth (C-02).
_SEEN_IDS_TTL = 86400  # 24 hours
_activation_seen_ids: dict[ModelId, tuple[set[ModelId], float]] = {}


def get_seen_ids(session_id: SessionId) -> set[ModelId]:
    """Get the set of activation IDs for a session, with TTL eviction."""
    _evict_stale_seen_ids()
    entry = _activation_seen_ids.get(session_id)
    return entry[0] if entry else set()


def set_seen_ids(session_id: SessionId, ids: set[ModelId]) -> None:
    """Store activation IDs for a session."""
    _activation_seen_ids[session_id] = (ids, time.monotonic())


def _evict_stale_seen_ids() -> None:
    """Remove entries older than TTL."""
    now = time.monotonic()
    stale = [k for k, (_, ts) in _activation_seen_ids.items() if now - ts > _SEEN_IDS_TTL]
    for k in stale:
        del _activation_seen_ids[k]
