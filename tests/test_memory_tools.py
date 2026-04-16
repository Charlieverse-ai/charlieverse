"""Tests for the memory MCP tool functions.

The public surface collapsed from nine `remember_*` helpers plus a `recall`
tool into a unified `save_memory` + `search_memories` pair. These tests
cover the current surface: save_memory (per entity type), update_memory,
forget_memory, pin/unpin (entity + knowledge), and search_memories.
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

import pytest
from fastmcp.server.dependencies import CurrentContext

from charlieverse.memory.entities import EntityId, EntityType
from charlieverse.memory.entities.mcp import (
    forget_memory,
    pin,
    save_memory,
    search_memories,
    update_memory,
)
from charlieverse.memory.sessions import SessionId
from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.server.responses.summaries import EntitySummary, StorySummary
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString

_SID = SessionId()


def _tags(*values: str) -> TagList:
    """Build a TagList from plain strings for test ergonomics."""
    return TagList([NonEmptyString(v) for v in values])


@pytest.fixture(autouse=True)
def _patch_stores(stores):
    """Route all Stores.from_context calls to the test stores."""
    with patch("charlieverse.memory.entities.mcp.Stores") as mock:
        mock.from_context.return_value = stores
        yield


# Use a fake context -- Stores.from_context is patched above
_CTX = CurrentContext()


# ---------------------------------------------------------------------------
# save_memory — one test per entity type
# ---------------------------------------------------------------------------


async def test_save_memory_decision(memory_store, mock_embed):
    result = await save_memory(
        type=EntityType.decision,
        content=NonEmptyString("use pytest for testing because it's the best"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_save_memory_solution(memory_store, mock_embed):
    await save_memory(
        type=EntityType.solution,
        content=NonEmptyString("Problem: import error. Solution: add __init__.py"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    entities = await memory_store.search("import error", limit=5)
    assert any(e.type == EntityType.solution for e in entities)


async def test_save_memory_preference(memory_store, mock_embed):
    result = await save_memory(
        type=EntityType.preference,
        content=NonEmptyString("prefers concise commit messages over verbose ones"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_save_memory_person(memory_store, mock_embed):
    result = await save_memory(
        type=EntityType.person,
        content=NonEmptyString("Alex -- lead engineer, likes async patterns"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_save_memory_milestone(memory_store, mock_embed):
    result = await save_memory(
        type=EntityType.milestone,
        content=NonEmptyString("first test suite passing — proves the pipeline works"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_save_memory_moment(memory_store, mock_embed):
    result = await save_memory(
        type=EntityType.moment,
        content=NonEmptyString("fixed a tricky async bug — satisfying deep focus"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_save_memory_project(memory_store, mock_embed):
    await save_memory(
        type=EntityType.project,
        content=NonEmptyString("Charlieverse — memory platform for AI"),
        session_id=_SID,
        tags=_tags("python", "mcp"),
        pinned=False,
        ctx=_CTX,
    )
    entities = await memory_store.search("Charlieverse", limit=5)
    assert any(e.type == EntityType.project for e in entities)
    assert any("python" in (e.tags or []) for e in entities)


async def test_save_memory_event(memory_store, mock_embed):
    await save_memory(
        type=EntityType.event,
        content=NonEmptyString("Fay Nutrition technical screen on March 20, 2026"),
        session_id=_SID,
        tags=_tags("career", "fay"),
        pinned=False,
        ctx=_CTX,
    )
    entities = await memory_store.search("Fay Nutrition", limit=5)
    assert any(e.type == EntityType.event for e in entities)


async def test_save_memory_pinned(memory_store, mock_embed):
    await save_memory(
        type=EntityType.decision,
        content=NonEmptyString("a load-bearing decision that must stay pinned"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=True,
        ctx=_CTX,
    )
    entities = await memory_store.search("load-bearing decision", limit=5)
    assert any(e.pinned for e in entities)


# ---------------------------------------------------------------------------
# update_memory
# ---------------------------------------------------------------------------


async def test_update_memory_changes_content(memory_store, mock_embed):
    from charlieverse.memory.entities import NewEntity

    entity = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("original decision content"),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )
    await update_memory(
        id=entity.id,
        session_id=_SID,
        content=NonEmptyString("revised decision content that is long enough to satisfy validation"),
        tags=_tags("test"),
        ctx=_CTX,
    )
    stored = await memory_store.get(entity.id)
    assert stored is not None
    assert "revised decision" in stored.content


async def test_update_memory_nonexistent_raises(memory_store, mock_embed):
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await update_memory(
            id=EntityId(),
            session_id=_SID,
            content=NonEmptyString("does not matter at all because this should fail"),
            tags=_tags("test"),
            ctx=_CTX,
        )


# ---------------------------------------------------------------------------
# forget (soft delete)
# ---------------------------------------------------------------------------


async def test_forget_removes_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import NewEntity

    entity = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("entity to forget from the store"),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )
    await forget_memory(id=entity.id, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is None


# ---------------------------------------------------------------------------
# pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import NewEntity

    entity = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("pin this decision for the test"),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )
    await pin(id=entity.id, pinned=True, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is not None
    assert stored.pinned is True


async def test_unpin_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import NewEntity

    entity = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("unpin this decision for the test"),
            tags=_tags("test"),
            pinned=True,
            created_session_id=_SID,
        )
    )
    await pin(id=entity.id, pinned=False, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is not None
    assert stored.pinned is False


async def test_pin_knowledge_article(knowledge_store, memory_store, mock_embed):
    from charlieverse.memory.knowledge.models import NewKnowledge

    article = NewKnowledge(
        topic=NonEmptyString("pinnable topic"),
        content=NonEmptyString("pin this knowledge article for the test"),
        created_session_id=_SID,
    )
    await knowledge_store.upsert(article)
    await pin(id=article.id, pinned=True, ctx=_CTX)
    stored = await knowledge_store.get(article.id)
    assert stored is not None
    assert stored.pinned is True


async def test_unpin_knowledge_article(knowledge_store, memory_store, mock_embed):
    from charlieverse.memory.knowledge.models import NewKnowledge

    article = NewKnowledge(
        topic=NonEmptyString("unpinnable topic"),
        content=NonEmptyString("unpin this knowledge article for the test"),
        pinned=True,
        created_session_id=_SID,
    )
    await knowledge_store.upsert(article)
    await pin(id=article.id, pinned=False, ctx=_CTX)
    stored = await knowledge_store.get(article.id)
    assert stored is not None
    assert stored.pinned is False


async def test_pin_nonexistent_id_raises(memory_store, knowledge_store):
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="No entity or knowledge article found"):
        await pin(id=EntityId(), pinned=True, ctx=_CTX)


# ---------------------------------------------------------------------------
# search_memories
# ---------------------------------------------------------------------------


async def test_search_memories_returns_list(memory_store, mock_embed):
    result = await search_memories(query=NonEmptyString("testing"), ctx=_CTX)
    assert isinstance(result, list)


async def test_search_memories_empty_db_returns_empty(memory_store, mock_embed):
    result = await search_memories(query=NonEmptyString("nothing stored in here"), ctx=_CTX)
    assert result == []


async def test_search_memories_finds_stored_entity(memory_store, mock_embed):
    await save_memory(
        type=EntityType.decision,
        content=NonEmptyString("use pytest for all the testing we do"),
        session_id=_SID,
        tags=_tags("test"),
        pinned=False,
        ctx=_CTX,
    )
    result = await search_memories(query=NonEmptyString("pytest testing"), ctx=_CTX)
    contents = [item.content for item in result if isinstance(item, EntitySummary)]
    assert any("pytest" in c for c in contents)


async def test_search_memories_ranks_recent_entities_higher(memory_store, mock_embed):
    """A newer entity should rank above an older one when both match the query."""
    from datetime import datetime, timedelta

    from charlieverse.memory.entities import NewEntity

    old = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("deploy strategy for servers in production"),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )
    # 10-day gap is enough to change ranking without either entity falling below
    # the relevance+recency score threshold used by _rank_by_relevance_and_recency.
    old_date = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    await memory_store.db.execute(
        "UPDATE entities SET created_at = ?, updated_at = ? WHERE id = ?",
        (old_date, old_date, old.id),
    )
    await memory_store.db.commit()

    recent = await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("deploy strategy for containers in production"),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )

    result = await search_memories(query=NonEmptyString("deploy strategy"), ctx=_CTX)
    entity_ids = [item.id for item in result if isinstance(item, EntitySummary)]
    assert len(entity_ids) >= 2
    assert entity_ids.index(recent.id) < entity_ids.index(old.id)


async def test_search_memories_finds_stories(memory_store, story_store, mock_embed):
    from charlieverse.memory.stories import NewStory, StoryTier

    story = NewStory(
        title=NonEmptyString("The Great Refactor"),
        content=NonEmptyString("Rewrote the entire memory pipeline from scratch using Python and FastMCP"),
        tier=StoryTier.daily,
        period_start="2026-03-20",
        period_end="2026-03-20",
    )
    await story_store.upsert(story)

    result = await search_memories(query=NonEmptyString("memory pipeline Python"), ctx=_CTX)
    story_results = [item for item in result if isinstance(item, StorySummary)]
    assert len(story_results) > 0
    assert any("Refactor" in s.title for s in story_results)


async def test_search_memories_truncates_long_entity_content(memory_store, mock_embed):
    from charlieverse.memory.entities import NewEntity

    await memory_store.create(
        NewEntity(
            type=EntityType.decision,
            content=NonEmptyString("x" * 2000),
            tags=_tags("test"),
            created_session_id=_SID,
        )
    )

    result = await search_memories(query=NonEmptyString("x" * 50), ctx=_CTX)
    for item in result:
        if isinstance(item, EntitySummary):
            assert len(item.content) <= 501  # 500 + ellipsis char
