"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import time

from charlieverse.memory.entities import EntityId
from charlieverse.memory.sessions import SessionId

# session_id -> (IDs delivered at activation, timestamp).
# Entries older than 24h are evicted on access to prevent unbounded growth (C-02).
_SEEN_IDS_TTL = 86400  # 24 hours
_activation_seen_ids: dict[SessionId, tuple[set[EntityId], float]] = {}

_enriched_topics: dict[SessionId, tuple[set[str], float]] = {}


def get_seen_ids(session_id: SessionId) -> set[EntityId]:
    """Get the set of activation IDs for a session, with TTL eviction."""
    _evict_stale_seen_ids()
    entry = _activation_seen_ids.get(session_id)
    return entry[0] if entry else set()


def set_seen_ids(session_id: SessionId, ids: set[EntityId]) -> None:
    """Store activation IDs for a session."""
    _activation_seen_ids[session_id] = (ids, time.monotonic())


def _evict_stale_seen_ids() -> None:
    """Remove entries older than TTL."""
    now = time.monotonic()
    stale = [k for k, (_, ts) in _activation_seen_ids.items() if now - ts > _SEEN_IDS_TTL]
    for k in stale:
        del _activation_seen_ids[k]

    stale = [k for k, (_, ts) in _enriched_topics.items() if now - ts > _SEEN_IDS_TTL]
    for k in stale:
        del _enriched_topics[k]


def process_enriched_topics(session_id: SessionId, topics: list[str]) -> list[str]:
    """Filter topics against what's already been enriched this session.

    Both the store and the check are lowercased so "Django" and "django"
    collapse. Accumulates over the session's TTL window so topics seen 10
    turns ago still dedupe.
    """
    seen = get_enriched_topics(session_id)
    lowered = {t.lower() for t in topics}
    new_topics = [t for t in topics if t.lower() not in seen]
    set_enriched_topics(session_id, seen | lowered)
    return new_topics


def get_enriched_topics(session_id: SessionId) -> set[str]:
    """Return the set of lowercased topics already enriched for this session."""
    _evict_stale_seen_ids()
    entry = _enriched_topics.get(session_id)
    return entry[0] if entry else set()


def set_enriched_topics(session_id: SessionId, topics: set[str]) -> None:
    """Store lowercased enriched topics for a session."""
    _enriched_topics[session_id] = (topics, time.monotonic())
