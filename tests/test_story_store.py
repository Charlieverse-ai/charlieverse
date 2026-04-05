"""CRUD and search tests for StoryStore."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from charlieverse.memory.stories import Story, StoryTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = UUID(int=0)
_ZERO_VEC = [0.0] * 384


def _story(
    title: str = "test story",
    content: str = "some story content that is long enough",
    tier: StoryTier = StoryTier.weekly,
    period_start: str = "2026-03-16",
    period_end: str = "2026-03-22",
    **kw,
) -> Story:
    return Story(
        title=title,
        content=content,
        tier=tier,
        period_start=period_start,
        period_end=period_end,
        **kw,
    )


@pytest.fixture(autouse=True)
def _mock_vec():
    """Patch encode_one globally so _sync_vec never loads the model."""
    with (
        patch(
            "charlieverse.memory.stories.store.encode_one",
            new=AsyncMock(return_value=_ZERO_VEC),
            create=True,
        ),
        patch(
            "charlieverse.embeddings.encode_one",
            new=AsyncMock(return_value=_ZERO_VEC),
        ),
        patch(
            "charlieverse.embeddings.tasks.encode_one",
            new=AsyncMock(return_value=_ZERO_VEC),
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_story(story_store):
    story = await story_store.create(_story())
    assert story.id is not None
    assert isinstance(story.id, UUID)


async def test_create_stores_content(story_store):
    s = await story_store.create(_story("my title", "the full story content here enough chars"))
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.title == "my title"
    assert fetched.content == "the full story content here enough chars"


async def test_create_stores_tier(story_store):
    s = await story_store.create(_story(tier=StoryTier.monthly))
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.tier == StoryTier.monthly


async def test_create_stores_tags(story_store):
    s = await story_store.create(_story(tags=["sprint", "bugfix"]))
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.tags == ["sprint", "bugfix"]


async def test_create_stores_session_id(story_store):
    sid = uuid4()
    s = await story_store.create(_story(session_id=sid, tier=StoryTier.session))
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.session_id == sid


# ---------------------------------------------------------------------------
# Get / list
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(story_store):
    result = await story_store.get(uuid4())
    assert result is None


async def test_list_returns_all_active(story_store):
    await story_store.create(_story("story one"))
    await story_store.create(_story("story two"))
    results = await story_store.list()
    assert len(results) >= 2


async def test_list_filters_by_tier(story_store):
    await story_store.create(_story(tier=StoryTier.weekly))
    await story_store.create(_story(tier=StoryTier.monthly))
    weekly = await story_store.list(tier=StoryTier.weekly)
    for s in weekly:
        assert s.tier == StoryTier.weekly


# ---------------------------------------------------------------------------
# Find by session
# ---------------------------------------------------------------------------


async def test_find_by_session(story_store):
    sid = uuid4()
    await story_store.create(_story(session_id=sid, tier=StoryTier.session))
    found = await story_store.find_by_session(sid)
    assert found is not None
    assert found.session_id == sid


async def test_find_by_session_returns_none_for_missing(story_store):
    result = await story_store.find_by_session(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Find by period
# ---------------------------------------------------------------------------


async def test_find_by_period(story_store):
    await story_store.create(_story(period_start="2026-03-16", period_end="2026-03-22"))
    results = await story_store.find_by_period("2026-03-16", "2026-03-22")
    assert len(results) >= 1


async def test_find_by_period_excludes_non_overlapping(story_store):
    await story_store.create(_story(period_start="2026-01-01", period_end="2026-01-07"))
    results = await story_store.find_by_period("2026-06-01", "2026-06-07")
    assert len(results) == 0


async def test_find_by_period_returns_all_workspaces(story_store):
    """Workspace is metadata, not a filter — find_by_period returns stories from all workspaces."""
    await story_store.create(_story("project-a story", workspace="/project/a"))
    await story_store.create(_story("project-b story", workspace="/project/b"))
    results = await story_store.find_by_period("2026-03-16", "2026-03-22", workspace="/project/a")
    workspaces = {s.workspace for s in results}
    assert "/project/a" in workspaces
    assert "/project/b" in workspaces


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def test_upsert_creates_new(story_store):
    s = await story_store.upsert(_story("brand new"))
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.title == "brand new"


async def test_upsert_updates_by_session_id(story_store):
    sid = uuid4()
    original = await story_store.create(_story("v1", session_id=sid, tier=StoryTier.session))
    updated = await story_store.upsert(_story("v2", session_id=sid, tier=StoryTier.session))
    assert updated.id == original.id
    fetched = await story_store.get(original.id)
    assert fetched is not None
    assert fetched.title == "v2"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(story_store):
    s = await story_store.create(_story("original title"))
    s.title = "updated title"
    s.content = "updated content that is long enough for the test"
    await story_store.update(s)
    fetched = await story_store.get(s.id)
    assert fetched is not None
    assert fetched.title == "updated title"


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_story(story_store):
    s = await story_store.create(_story())
    await story_store.delete(s.id)
    result = await story_store.get(s.id)
    assert result is None


async def test_soft_deleted_excluded_from_list(story_store):
    s = await story_store.create(_story("delete from list"))
    count_before = len(await story_store.list())
    await story_store.delete(s.id)
    count_after = len(await story_store.list())
    assert count_after == count_before - 1


# ---------------------------------------------------------------------------
# Search (FTS)
# ---------------------------------------------------------------------------


async def test_search_finds_story(story_store):
    await story_store.create(_story("python sprint", "we built pytest fixtures and ran them"))
    await story_store.rebuild_fts()
    results = await story_store.search("pytest")
    assert any("pytest" in r.content.lower() for r in results)


async def test_search_empty_query_returns_empty(story_store):
    await story_store.create(_story("something", "interesting content here yeah"))
    await story_store.rebuild_fts()
    results = await story_store.search("the")
    assert results == []


async def test_search_with_period_filter(story_store):
    await story_store.create(_story("march sprint", "unique xyzzy content for march", period_start="2026-03-16", period_end="2026-03-22"))
    await story_store.rebuild_fts()
    results = await story_store.search("xyzzy", period_start="2026-03-16", period_end="2026-03-22")
    assert len(results) >= 1


async def test_search_no_query_with_dates_falls_back_to_period(story_store):
    await story_store.create(_story(period_start="2026-03-16", period_end="2026-03-22"))
    results = await story_store.search("", period_start="2026-03-16", period_end="2026-03-22")
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# Get all-time
# ---------------------------------------------------------------------------


async def test_get_all_time(story_store):
    await story_store.create(_story("The Full Arc", tier=StoryTier.all_time, period_start="2025-06-01", period_end="2026-03-22"))
    result = await story_store.get_all_time()
    assert result is not None
    assert result.tier == StoryTier.all_time


async def test_get_all_time_returns_none_when_missing(story_store):
    result = await story_store.get_all_time()
    assert result is None
