"""CRUD tests for SessionStore."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from charlieverse.models import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(
    what_happened: str | None = "Built some stuff",
    for_next_session: str | None = "Keep building",
    **kw,
) -> Session:
    return Session(
        what_happened=what_happened,
        for_next_session=for_next_session,
        **kw,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_session(session_store):
    s = await session_store.create(_session())
    assert s.id is not None
    assert isinstance(s.id, UUID)


async def test_create_stores_fields(session_store):
    s = await session_store.create(_session(
        what_happened="fixed bugs",
        for_next_session="write tests",
        workspace="/some/path",
        tags=["bugfix"],
    ))
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.what_happened == "fixed bugs"
    assert fetched.for_next_session == "write tests"
    assert fetched.workspace == "/some/path"
    assert fetched.tags == ["bugfix"]


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(session_store):
    result = await session_store.get(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(session_store):
    s = await session_store.create(_session())
    s.what_happened = "updated description"
    await session_store.update(s)
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.what_happened == "updated description"


async def test_update_changes_tags(session_store):
    s = await session_store.create(_session(tags=["old"]))
    s.tags = ["new", "tags"]
    await session_store.update(s)
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.tags == ["new", "tags"]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def test_upsert_creates_new(session_store):
    s = _session()
    result = await session_store.upsert(s)
    fetched = await session_store.get(result.id)
    assert fetched is not None


async def test_upsert_updates_existing(session_store):
    s = await session_store.create(_session(what_happened="v1"))
    s.what_happened = "v2"
    await session_store.upsert(s)
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.what_happened == "v2"


# ---------------------------------------------------------------------------
# Recent
# ---------------------------------------------------------------------------


async def test_recent_returns_sessions_with_content(session_store):
    await session_store.create(_session())
    await session_store.create(_session())
    results = await session_store.recent(limit=10)
    assert len(results) >= 2


async def test_recent_excludes_empty_sessions(session_store):
    # Session with no what_happened should be excluded
    await session_store.create(Session())
    await session_store.create(_session())
    results = await session_store.recent(limit=10)
    assert all(s.what_happened is not None for s in results)


async def test_recent_returns_all_workspaces(session_store):
    """Workspace is metadata, not a filter — all sessions returned regardless."""
    await session_store.create(_session(workspace="/project/a"))
    await session_store.create(_session(workspace="/project/b"))
    results = await session_store.recent(limit=10, workspace="/project/a")
    workspaces = {s.workspace for s in results}
    assert "/project/a" in workspaces
    assert "/project/b" in workspaces


# ---------------------------------------------------------------------------
# Recent within range
# ---------------------------------------------------------------------------


async def test_recent_within_range_returns_matching(session_store):
    await session_store.create(_session())
    # Use a wide range that covers today
    results = await session_store.recent_within_range("2020-01-01", "2030-12-31")
    assert len(results) >= 1


async def test_recent_within_range_excludes_outside(session_store):
    await session_store.create(_session())
    # Range in the far past — should find nothing
    results = await session_store.recent_within_range("2000-01-01", "2000-12-31")
    assert len(results) == 0


async def test_recent_within_range_excludes_incomplete(session_store):
    # Session with no for_next_session should be excluded
    await session_store.create(Session(what_happened="partial save"))
    results = await session_store.recent_within_range("2020-01-01", "2030-12-31")
    assert all(s.for_next_session is not None for s in results)


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_session(session_store):
    s = await session_store.create(_session())
    await session_store.delete(s.id)
    result = await session_store.get(s.id)
    assert result is None


async def test_soft_deleted_excluded_from_recent(session_store):
    s = await session_store.create(_session())
    count_before = len(await session_store.recent(limit=100))
    await session_store.delete(s.id)
    count_after = len(await session_store.recent(limit=100))
    assert count_after == count_before - 1
