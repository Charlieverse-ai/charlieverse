"""Tests for charlieverse.server.utils.seen_models — TTL-evicted activation ID cache."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from charlieverse.memory.entities import EntityId
from charlieverse.memory.sessions import SessionId
from charlieverse.server.utils import seen_models
from charlieverse.server.utils.seen_models import get_seen_ids, set_seen_ids


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the module-level cache before every test."""
    seen_models._activation_seen_ids.clear()
    yield
    seen_models._activation_seen_ids.clear()


# ---------------------------------------------------------------------------
# get / set round trip
# ---------------------------------------------------------------------------


def test_get_seen_ids_unknown_session_returns_empty_set():
    assert get_seen_ids(SessionId()) == set()


def test_set_then_get_round_trips():
    sid = SessionId()
    ids = {EntityId(), EntityId()}
    set_seen_ids(sid, ids)
    assert get_seen_ids(sid) == ids


def test_get_seen_ids_returns_empty_when_cache_cleared():
    sid = SessionId()
    set_seen_ids(sid, {EntityId()})
    seen_models._activation_seen_ids.clear()
    assert get_seen_ids(sid) == set()


def test_set_seen_ids_replaces_existing_entry():
    sid = SessionId()
    set_seen_ids(sid, {EntityId()})
    new_ids = {EntityId(), EntityId(), EntityId()}
    set_seen_ids(sid, new_ids)
    assert get_seen_ids(sid) == new_ids


def test_separate_sessions_keep_separate_sets():
    a = SessionId()
    b = SessionId()
    a_ids = {EntityId()}
    b_ids = {EntityId(), EntityId()}
    set_seen_ids(a, a_ids)
    set_seen_ids(b, b_ids)
    assert get_seen_ids(a) == a_ids
    assert get_seen_ids(b) == b_ids


# ---------------------------------------------------------------------------
# TTL eviction — entries older than 24h are evicted on any get access
# ---------------------------------------------------------------------------


def test_get_evicts_stale_entries():
    sid = SessionId()
    ids = {EntityId()}

    with patch.object(seen_models, "time") as mock_time:
        mock_time.monotonic.return_value = 0.0
        set_seen_ids(sid, ids)

        # Advance past TTL
        mock_time.monotonic.return_value = seen_models._SEEN_IDS_TTL + 1
        # Any get access triggers eviction
        assert get_seen_ids(sid) == set()

    # Session entry is gone from the underlying dict
    assert sid not in seen_models._activation_seen_ids


def test_get_does_not_evict_fresh_entries():
    sid = SessionId()
    ids = {EntityId()}

    with patch.object(seen_models, "time") as mock_time:
        mock_time.monotonic.return_value = 0.0
        set_seen_ids(sid, ids)

        # Advance but stay under TTL
        mock_time.monotonic.return_value = seen_models._SEEN_IDS_TTL - 1
        assert get_seen_ids(sid) == ids

    assert sid in seen_models._activation_seen_ids


def test_eviction_only_removes_stale_entries():
    fresh = SessionId()
    stale = SessionId()

    with patch.object(seen_models, "time") as mock_time:
        mock_time.monotonic.return_value = 0.0
        set_seen_ids(stale, {EntityId()})

        mock_time.monotonic.return_value = seen_models._SEEN_IDS_TTL - 10
        set_seen_ids(fresh, {EntityId()})

        # Advance so stale is past TTL but fresh is not
        mock_time.monotonic.return_value = seen_models._SEEN_IDS_TTL + 5
        get_seen_ids(fresh)  # triggers eviction

    assert stale not in seen_models._activation_seen_ids
    assert fresh in seen_models._activation_seen_ids


def test_ttl_default_is_24_hours():
    # Locking in the contract — anything longer means stale data lingers.
    assert seen_models._SEEN_IDS_TTL == 86400


# ---------------------------------------------------------------------------
# Integration: real monotonic clock
# ---------------------------------------------------------------------------


def test_real_clock_entries_survive_short_interval():
    sid = SessionId()
    ids = {EntityId()}
    set_seen_ids(sid, ids)
    time.sleep(0.01)
    assert get_seen_ids(sid) == ids
