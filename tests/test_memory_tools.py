"""Tests for the memory MCP tool functions."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

import pytest
from fastmcp.dependencies import CurrentContext

from charlieverse.memory.entities import EntityId
from charlieverse.memory.entities.mcp import (
    forget_memory,
    pin,
    recall,
    remember_decision,
    remember_event,
    remember_milestone,
    remember_moment,
    remember_person,
    remember_preference,
    remember_project,
    remember_solution,
    update_memory,
)
from charlieverse.memory.sessions import SessionId
from charlieverse.server.responses import ModelListResponse
from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.types.lists import TagList

_SID = SessionId()


def _items(response: ModelListResponse) -> list[dict]:
    """Parse the JSON body of a ModelListResponse into a list of dicts."""
    import json

    assert isinstance(response.body, bytes)
    return json.loads(response.body)


@pytest.fixture(autouse=True)
def _patch_stores(stores):
    """Route all Stores.from_context calls to the test stores."""
    with patch("charlieverse.memory.entities.mcp.Stores") as mock:
        mock.from_context.return_value = stores
        yield


# Use a fake context -- Stores.from_context is patched above
_CTX = CurrentContext()


# ---------------------------------------------------------------------------
# remember_decision
# ---------------------------------------------------------------------------


async def test_remember_decision_returns_permalink(memory_store, mock_embed):
    result = await remember_decision(
        content="use pytest for testing",
        rationale="solid test framework",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)
    assert result.url is not None


async def test_remember_decision_with_rationale(memory_store, mock_embed):
    await remember_decision(
        content="use black for formatting",
        rationale="consistent style across the team",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("black formatting", limit=5)
    match = [e for e in entities if "Rationale:" in e.content]
    assert len(match) > 0


async def test_remember_decision_with_tags(memory_store, mock_embed):
    await remember_decision(
        content="prefer async over sync",
        rationale="better for I/O bound work",
        session_id=_SID,
        tags=TagList(["architecture", "python"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("async sync", limit=5)
    assert any("architecture" in (e.tags or []) for e in entities)


# ---------------------------------------------------------------------------
# remember_solution
# ---------------------------------------------------------------------------


async def test_remember_solution_stores_problem_and_solution(memory_store, mock_embed):
    await remember_solution(
        problem="import error on startup",
        solution="add __init__.py to package dir",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("import error", limit=5)
    match = [e for e in entities if "Problem:" in e.content and "Solution:" in e.content]
    assert len(match) > 0


# ---------------------------------------------------------------------------
# remember_preference
# ---------------------------------------------------------------------------


async def test_remember_preference(memory_store, mock_embed):
    result = await remember_preference(
        content="prefers concise commit messages",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


# ---------------------------------------------------------------------------
# remember_person
# ---------------------------------------------------------------------------


async def test_remember_person(memory_store, mock_embed):
    result = await remember_person(
        content="Alex -- lead engineer, likes async patterns",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


# ---------------------------------------------------------------------------
# remember_milestone
# ---------------------------------------------------------------------------


async def test_remember_milestone(memory_store, mock_embed):
    result = await remember_milestone(
        milestone="first test suite passing",
        significance="proves the pipeline works",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_remember_milestone_with_significance(memory_store, mock_embed):
    await remember_milestone(
        milestone="deployed to production",
        significance="first real deployment with zero downtime",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("deployed production", limit=5)
    match = [e for e in entities if "Significance:" in e.content]
    assert len(match) > 0


# ---------------------------------------------------------------------------
# remember_moment
# ---------------------------------------------------------------------------


async def test_remember_moment(memory_store, mock_embed):
    result = await remember_moment(
        moment="pair programming session with Alex",
        feeling="satisfying collaboration",
        context="afternoon debugging session",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_remember_moment_with_feeling_and_context(memory_store, mock_embed):
    await remember_moment(
        moment="fixed a tricky async bug",
        feeling="satisfying deep focus",
        context="late night debugging session",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("async bug", limit=5)
    match = [e for e in entities if "Feeling:" in e.content and "Context:" in e.content]
    assert len(match) > 0


# ---------------------------------------------------------------------------
# remember_project
# ---------------------------------------------------------------------------


async def test_remember_project(memory_store, mock_embed):
    result = await remember_project(
        name="Charlieverse",
        details="memory platform for AI",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_remember_project_with_details(memory_store, mock_embed):
    await remember_project(
        name="CharlieMail",
        details="Inter-Charlie messaging platform deployed on Railway",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("messaging platform", limit=5)
    match = [e for e in entities if "Inter-Charlie messaging" in e.content]
    assert len(match) > 0


async def test_remember_project_with_tags(memory_store, mock_embed):
    await remember_project(
        name="Charlieverse",
        details="memory platform for AI",
        session_id=_SID,
        tags=TagList(["python", "mcp"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("Charlieverse", limit=5)
    assert any("python" in (e.tags or []) for e in entities)


async def test_remember_project_type(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType

    await remember_project(
        name="test project for typing",
        details="validate project type storage",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("test project", limit=5)
    assert any(e.type == EntityType.project for e in entities)


# ---------------------------------------------------------------------------
# remember_event
# ---------------------------------------------------------------------------


async def test_remember_event(memory_store, mock_embed):
    result = await remember_event(
        what="Fay Nutrition technical screen",
        when="March 20, 2026",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    assert isinstance(result, PermalinkResponse)


async def test_remember_event_stores_what_and_when(memory_store, mock_embed):
    await remember_event(
        what="shipped v1.10.0",
        when="March 22, 2026",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("shipped", limit=5)
    match = [e for e in entities if "What:" in e.content and "When:" in e.content]
    assert len(match) > 0


async def test_remember_event_with_all_fields(memory_store, mock_embed):
    await remember_event(
        what="technical interview",
        when="March 20, 2026",
        who="Brayden Harris and Kyle",
        where="remote",
        why="iOS engineer position",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("technical interview", limit=5)
    match = [e for e in entities if "Who:" in e.content and "Where:" in e.content and "Why:" in e.content]
    assert len(match) > 0


async def test_remember_event_without_optional_fields(memory_store, mock_embed):
    await remember_event(
        what="standup meeting",
        when="every Monday 9am",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("standup meeting", limit=5)
    assert len(entities) > 0
    for e in entities:
        if "standup" in e.content:
            assert "Who:" not in e.content
            assert "Where:" not in e.content
            assert "Why:" not in e.content


async def test_remember_event_with_tags(memory_store, mock_embed):
    await remember_event(
        what="job interview",
        when="next week sometime",
        session_id=_SID,
        tags=TagList(["career", "fay"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("job interview", limit=5)
    assert any("career" in (e.tags or []) for e in entities)


async def test_remember_event_type(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType

    await remember_event(
        what="some event happening",
        when="today or tomorrow",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    entities = await memory_store.search("some event", limit=5)
    assert any(e.type == EntityType.event for e in entities)


# ---------------------------------------------------------------------------
# update_memory
# ---------------------------------------------------------------------------


async def test_update_memory_changes_content(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType, NewEntity

    entity = await memory_store.create(NewEntity(type=EntityType.decision, content="original decision", tags=TagList(["test"]), created_session_id=_SID))
    await update_memory(
        id=entity.id,
        session_id=_SID,
        content="revised decision content that is long enough to satisfy validation",
        tags=TagList(["test"]),
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
            content="does not matter at all because this should fail",
            tags=TagList(["test"]),
            ctx=_CTX,
        )


# ---------------------------------------------------------------------------
# forget (soft delete)
# ---------------------------------------------------------------------------


async def test_forget_removes_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType, NewEntity

    entity = await memory_store.create(NewEntity(type=EntityType.decision, content="entity to forget", tags=TagList(["test"]), created_session_id=_SID))
    await forget_memory(id=entity.id, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is None


# ---------------------------------------------------------------------------
# pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType, NewEntity

    entity = await memory_store.create(NewEntity(type=EntityType.decision, content="pin this decision", tags=TagList(["test"]), created_session_id=_SID))
    await pin(id=entity.id, pinned=True, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is not None
    assert stored.pinned is True


async def test_unpin_entity(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType, NewEntity

    entity = await memory_store.create(
        NewEntity(type=EntityType.decision, content="unpin this decision", tags=TagList(["test"]), pinned=True, created_session_id=_SID)
    )
    await pin(id=entity.id, pinned=False, ctx=_CTX)
    stored = await memory_store.get(entity.id)
    assert stored is not None
    assert stored.pinned is False


async def test_pin_knowledge_article(knowledge_store, memory_store, mock_embed):
    from charlieverse.memory.knowledge.models import NewKnowledge

    article = NewKnowledge(
        topic="pinnable topic",
        content="pin this knowledge",
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
        topic="unpinnable topic",
        content="unpin this knowledge",
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
# recall
# ---------------------------------------------------------------------------


async def test_recall_returns_model_list(memory_store, mock_embed):
    result = await recall(query="testing", ctx=_CTX)
    assert isinstance(result, ModelListResponse)


async def test_recall_empty_db_returns_empty(memory_store, mock_embed):
    result = await recall(query="nothing here", ctx=_CTX)
    assert _items(result) == []


async def test_recall_finds_stored_entity(memory_store, mock_embed):
    await remember_decision(
        content="use pytest for all testing",
        rationale="best test framework",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    result = await recall(query="pytest testing", ctx=_CTX)
    items = _items(result)
    contents = [item.get("content", "") for item in items]
    assert any("pytest" in c for c in contents)


async def test_recall_with_type_filter(memory_store, mock_embed):
    await remember_decision(
        content="a decision about testing",
        rationale="test rationale here",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    await remember_preference(
        content="a preference about testing",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    result = await recall(query="testing", type="decision", ctx=_CTX)
    for item in _items(result):
        if "type" in item:
            assert item["type"] == "decision"


async def test_recall_deduplicates_results(memory_store, mock_embed):
    await remember_decision(
        content="unique deduplication test content",
        rationale="for testing dedup",
        session_id=_SID,
        tags=TagList(["test"]),
        ctx=_CTX,
    )
    result = await recall(query="unique deduplication test content", ctx=_CTX)
    ids = [item["id"] for item in _items(result) if "type" in item]
    assert len(ids) == len(set(ids))


async def test_recall_ranks_recent_entities_higher(memory_store, mock_embed):
    """A newer entity should rank above an older one when both match the query."""
    from datetime import datetime, timedelta

    from charlieverse.memory.entities import EntityType, NewEntity

    old = await memory_store.create(NewEntity(type=EntityType.decision, content="deploy strategy for servers", tags=TagList(["test"]), created_session_id=_SID))
    old_date = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    await memory_store.db.execute(
        "UPDATE entities SET created_at = ?, updated_at = ? WHERE id = ?",
        (old_date, old_date, old.id),
    )
    await memory_store.db.commit()

    recent = await memory_store.create(
        NewEntity(type=EntityType.decision, content="deploy strategy for containers", tags=TagList(["test"]), created_session_id=_SID)
    )

    result = await recall(query="deploy strategy", ctx=_CTX)
    entity_ids = [item["id"] for item in _items(result) if "type" in item]
    assert len(entity_ids) >= 2
    assert entity_ids.index(str(recent.id)) < entity_ids.index(str(old.id))


# ---------------------------------------------------------------------------
# recall -- story search
# ---------------------------------------------------------------------------


async def test_recall_searches_stories(memory_store, story_store, mock_embed):
    from charlieverse.memory.stories import NewStory, StoryTier

    story = NewStory(
        title="The Great Refactor",
        content="Rewrote the entire memory pipeline from scratch using Python and FastMCP",
        tier=StoryTier.daily,
        period_start="2026-03-20",
        period_end="2026-03-20",
    )
    await story_store.upsert(story)

    result = await recall(query="memory pipeline Python", ctx=_CTX)
    story_results = [item for item in _items(result) if "title" in item]
    assert len(story_results) > 0
    assert any("Refactor" in s["title"] for s in story_results)


async def test_recall_stories_capped_at_five(memory_store, story_store, mock_embed):
    from charlieverse.memory.stories import NewStory, StoryTier

    for i in range(10):
        story = NewStory(
            title=f"Story about widgets number {i}",
            content=f"A story about building widgets iteration {i} with plenty of detail to pass",
            tier=StoryTier.session,
            period_start="2026-03-20",
            period_end="2026-03-20",
        )
        await story_store.upsert(story)

    result = await recall(query="widgets", ctx=_CTX)
    story_results = [item for item in _items(result) if "title" in item]
    assert len(story_results) <= 5


# ---------------------------------------------------------------------------
# recall -- content truncation
# ---------------------------------------------------------------------------


async def test_recall_truncates_long_entity_content(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType, NewEntity

    await memory_store.create(NewEntity(type=EntityType.decision, content="x" * 2000, tags=TagList(["test"]), created_session_id=_SID))

    result = await recall(query="x" * 50, ctx=_CTX)
    for item in _items(result):
        if "type" in item:  # entity summary
            assert len(item["content"]) <= 301  # 300 + ellipsis char


async def test_recall_truncates_long_knowledge_content(memory_store, knowledge_store, mock_embed):
    from charlieverse.memory.knowledge.models import NewKnowledge

    article = NewKnowledge(
        topic="long topic",
        content="y" * 5000,
        created_session_id=_SID,
    )
    await knowledge_store.upsert(article)

    result = await recall(query="long topic", ctx=_CTX)
    for item in _items(result):
        if "truncated" in item and "type" not in item and "title" not in item:  # knowledge summary
            assert len(item["content"]) <= 501  # 500 + ellipsis char
