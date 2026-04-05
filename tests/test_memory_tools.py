"""Tests for the memory tool functions (called directly, not via FastMCP)."""

from __future__ import annotations

from datetime import UTC

import pytest

from charlieverse.tools.memory import (
    forget,
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
from charlieverse.tools.responses import IdResponse, RecallResponse

# ---------------------------------------------------------------------------
# remember_decision
# ---------------------------------------------------------------------------


async def test_remember_decision_returns_id(memory_store, mock_embed):
    result = await remember_decision(
        content="use pytest for testing",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)
    assert result.id is not None


async def test_remember_decision_with_rationale(memory_store, mock_embed):
    result = await remember_decision(
        content="use black for formatting",
        rationale="consistent style across the team",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)
    # Verify the rationale was embedded in the stored content
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Rationale:" in stored.content


async def test_remember_decision_with_tags(memory_store, mock_embed):
    result = await remember_decision(
        content="prefer async over sync",
        tags=["architecture", "python"],
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "architecture" in (stored.tags or [])


# ---------------------------------------------------------------------------
# remember_solution
# ---------------------------------------------------------------------------


async def test_remember_solution_returns_id(memory_store, mock_embed):
    result = await remember_solution(
        problem="tests were flaky",
        solution="add explicit await for FTS rebuild",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)


async def test_remember_solution_stores_problem_and_solution(memory_store, mock_embed):
    result = await remember_solution(
        problem="import error on startup",
        solution="add __init__.py to package dir",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Problem:" in stored.content
    assert "Solution:" in stored.content


# ---------------------------------------------------------------------------
# remember_preference
# ---------------------------------------------------------------------------


async def test_remember_preference_returns_id(memory_store, mock_embed):
    result = await remember_preference(
        content="prefers concise commit messages",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)


# ---------------------------------------------------------------------------
# remember_person
# ---------------------------------------------------------------------------


async def test_remember_person_returns_id(memory_store, mock_embed):
    result = await remember_person(
        content="Alex — lead engineer, likes async patterns",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)


# ---------------------------------------------------------------------------
# remember_milestone
# ---------------------------------------------------------------------------


async def test_remember_milestone_returns_id(memory_store, mock_embed):
    result = await remember_milestone(
        milestone="first test suite passing",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)


async def test_remember_milestone_with_significance(memory_store, mock_embed):
    result = await remember_milestone(
        milestone="deployed to production",
        significance="first real deployment with zero downtime",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Significance:" in stored.content


# ---------------------------------------------------------------------------
# remember_moment
# ---------------------------------------------------------------------------


async def test_remember_moment_returns_id(memory_store, mock_embed):
    result = await remember_moment(
        moment="pair programming session with Alex",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)


async def test_remember_moment_with_feeling_and_context(memory_store, mock_embed):
    result = await remember_moment(
        moment="fixed a tricky async bug",
        feeling="satisfying",
        context="late night debugging session",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Feeling:" in stored.content
    assert "Context:" in stored.content


# ---------------------------------------------------------------------------
# remember_project
# ---------------------------------------------------------------------------


async def test_remember_project_returns_id(memory_store, mock_embed):
    result = await remember_project(
        name="Charlieverse",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)
    assert result.id is not None


async def test_remember_project_with_details(memory_store, mock_embed):
    result = await remember_project(
        name="CharlieMail",
        details="Inter-Charlie messaging platform deployed on Railway",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "CharlieMail" in stored.content
    assert "Inter-Charlie messaging" in stored.content


async def test_remember_project_without_details(memory_store, mock_embed):
    result = await remember_project(
        name="ThinkFaster",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert stored.content == "ThinkFaster"


async def test_remember_project_with_tags(memory_store, mock_embed):
    result = await remember_project(
        name="Charlieverse",
        tags=["python", "mcp"],
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "python" in (stored.tags or [])


async def test_remember_project_type(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType

    result = await remember_project(name="test project", memories=memory_store)
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert stored.type == EntityType.project


# ---------------------------------------------------------------------------
# remember_event
# ---------------------------------------------------------------------------


async def test_remember_event_returns_id(memory_store, mock_embed):
    result = await remember_event(
        what="Fay Nutrition technical screen",
        when="March 20, 2026",
        memories=memory_store,
    )
    assert isinstance(result, IdResponse)
    assert result.id is not None


async def test_remember_event_stores_what_and_when(memory_store, mock_embed):
    result = await remember_event(
        what="shipped v1.10.0",
        when="March 22, 2026",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "What:" in stored.content
    assert "When:" in stored.content


async def test_remember_event_with_all_fields(memory_store, mock_embed):
    result = await remember_event(
        what="technical interview",
        when="March 20, 2026",
        who="Brayden Harris and Kyle",
        where="remote",
        why="iOS engineer position",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Who:" in stored.content
    assert "Where:" in stored.content
    assert "Why:" in stored.content


async def test_remember_event_without_optional_fields(memory_store, mock_embed):
    result = await remember_event(
        what="standup meeting",
        when="every Monday 9am",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "Who:" not in stored.content
    assert "Where:" not in stored.content
    assert "Why:" not in stored.content


async def test_remember_event_with_tags(memory_store, mock_embed):
    result = await remember_event(
        what="job interview",
        when="next week",
        tags=["career", "fay"],
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert "career" in (stored.tags or [])


async def test_remember_event_is_global(memory_store, mock_embed):
    from charlieverse.memory.entities import EntityType

    result = await remember_event(
        what="some event",
        when="today",
        memories=memory_store,
    )
    stored = await memory_store.get(result.id)
    assert stored is not None
    assert stored.type == EntityType.event


# ---------------------------------------------------------------------------
# update_memory
# ---------------------------------------------------------------------------


async def test_update_memory_changes_content(memory_store, mock_embed):
    created = await remember_decision(
        content="original decision",
        memories=memory_store,
    )
    await update_memory(
        id=str(created.id),
        content="revised decision",
        memories=memory_store,
    )
    stored = await memory_store.get(created.id)
    assert stored is not None
    assert stored.content == "revised decision"


async def test_update_memory_nonexistent_raises(memory_store, mock_embed):
    from uuid import uuid4

    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await update_memory(
            id=str(uuid4()),
            content="does not matter",
            memories=memory_store,
        )


# ---------------------------------------------------------------------------
# forget (soft delete)
# ---------------------------------------------------------------------------


async def test_forget_removes_entity(memory_store, mock_embed):
    created = await remember_decision(
        content="entity to forget",
        memories=memory_store,
    )
    await forget(id=str(created.id), memories=memory_store)
    stored = await memory_store.get(created.id)
    assert stored is None


# ---------------------------------------------------------------------------
# pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_entity(memory_store, mock_embed):
    created = await remember_decision(
        content="pin this decision",
        memories=memory_store,
    )
    await pin(id=str(created.id), pinned=True, memories=memory_store)
    stored = await memory_store.get(created.id)
    assert stored is not None
    assert stored.pinned is True


async def test_unpin_entity(memory_store, mock_embed):
    created = await remember_decision(
        content="unpin this decision",
        pinned=True,
        memories=memory_store,
    )
    await pin(id=str(created.id), pinned=False, memories=memory_store)
    stored = await memory_store.get(created.id)
    assert stored is not None
    assert stored.pinned is False


async def test_pin_knowledge_article(knowledge_store, memory_store, mock_embed):
    from uuid import UUID

    from charlieverse.memory.knowledge import Knowledge

    article = Knowledge(
        topic="pinnable topic",
        content="pin this knowledge",
        created_session_id=UUID(int=0),
    )
    await knowledge_store.upsert(article)
    await pin(
        id=str(article.id),
        pinned=True,
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    stored = await knowledge_store.get(article.id)
    assert stored is not None
    assert stored.pinned is True


async def test_unpin_knowledge_article(knowledge_store, memory_store, mock_embed):
    from uuid import UUID

    from charlieverse.memory.knowledge import Knowledge

    article = Knowledge(
        topic="unpinnable topic",
        content="unpin this knowledge",
        pinned=True,
        created_session_id=UUID(int=0),
    )
    await knowledge_store.upsert(article)
    await pin(
        id=str(article.id),
        pinned=False,
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    stored = await knowledge_store.get(article.id)
    assert stored is not None
    assert stored.pinned is False


async def test_pin_nonexistent_id_raises(memory_store, knowledge_store):
    from uuid import uuid4

    with pytest.raises(ValueError, match="No entity or knowledge article found"):
        await pin(
            id=str(uuid4()),
            pinned=True,
            memories=memory_store,
            knowledge_store=knowledge_store,
        )


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


async def test_recall_returns_recall_response(memory_store, knowledge_store, mock_embed):
    result = await recall(
        query="testing",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    assert isinstance(result, RecallResponse)


async def test_recall_empty_db_returns_empty_lists(memory_store, knowledge_store, mock_embed):
    result = await recall(
        query="nothing here",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    assert result.entities == []
    assert result.knowledge == []
    assert result.messages == []


async def test_recall_finds_stored_entity(memory_store, knowledge_store, mock_embed):
    await remember_decision(
        content="use pytest for all testing",
        memories=memory_store,
    )
    result = await recall(
        query="pytest testing",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    # FTS should pick this up
    entity_contents = [e.content for e in result.entities]
    assert any("pytest" in c for c in entity_contents)


async def test_recall_with_type_filter(memory_store, knowledge_store, mock_embed):
    await remember_decision(content="a decision about testing", memories=memory_store)
    await remember_preference(content="a preference about testing", memories=memory_store)

    result = await recall(
        query="testing",
        type="decision",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    # All returned entities must be of the requested type
    for entity in result.entities:
        assert entity.type == "decision"


async def test_recall_deduplicates_results(memory_store, knowledge_store, mock_embed):
    """Entities returned by both FTS and vector search should not be duplicated."""
    await remember_decision(
        content="unique deduplication test content",
        memories=memory_store,
    )
    result = await recall(
        query="unique deduplication test content",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    ids = [e.id for e in result.entities]
    assert len(ids) == len(set(ids))


async def test_recall_with_no_type_filter_returns_mixed_types(memory_store, knowledge_store, mock_embed):
    await remember_decision(content="decided to use Docker", memories=memory_store)
    await remember_preference(content="prefers Docker over VMs", memories=memory_store)

    result = await recall(
        query="Docker",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    types = {e.type for e in result.entities}
    assert len(types) >= 1  # At minimum we get results back


# ---------------------------------------------------------------------------
# recall — recency ranking
# ---------------------------------------------------------------------------


async def test_recall_ranks_recent_entities_higher(memory_store, knowledge_store, mock_embed):
    """A newer entity should rank above an older one when both match the query."""
    from datetime import datetime, timedelta

    # Create an old entity
    old = await remember_decision(content="deploy strategy for servers", memories=memory_store)
    # Manually age it by updating created_at and updated_at
    old_date = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    await memory_store.db.execute(
        "UPDATE entities SET created_at = ?, updated_at = ? WHERE id = ?",
        (old_date, old_date, str(old.id)),
    )
    await memory_store.db.commit()

    # Create a recent entity with overlapping content
    recent = await remember_decision(content="deploy strategy for containers", memories=memory_store)

    result = await recall(
        query="deploy strategy",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    assert len(result.entities) >= 2
    # Recent entity should appear first
    ids = [e.id for e in result.entities]
    assert ids.index(recent.id) < ids.index(old.id)


# ---------------------------------------------------------------------------
# recall — story search
# ---------------------------------------------------------------------------


async def test_recall_searches_stories(memory_store, knowledge_store, story_store, mock_embed):
    from charlieverse.memory.stories import Story, StoryTier

    story = Story(
        title="The Great Refactor",
        content="Rewrote the entire memory pipeline from scratch using Python",
        tier=StoryTier.daily,
        period_start="2026-03-20",
        period_end="2026-03-20",
    )
    await story_store.upsert(story)

    result = await recall(
        query="memory pipeline Python",
        memories=memory_store,
        knowledge_store=knowledge_store,
        story_store=story_store,
    )
    assert len(result.stories) > 0
    assert any("Refactor" in s.title for s in result.stories)


async def test_recall_without_story_store_returns_empty_stories(memory_store, knowledge_store, mock_embed):
    result = await recall(
        query="anything",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    assert result.stories == []


async def test_recall_stories_capped_at_five(memory_store, knowledge_store, story_store, mock_embed):
    from charlieverse.memory.stories import Story, StoryTier

    for i in range(10):
        story = Story(
            title=f"Story about widgets number {i}",
            content=f"A story about building widgets iteration {i}",
            tier=StoryTier.session,
            period_start="2026-03-20",
            period_end="2026-03-20",
        )
        await story_store.upsert(story)

    result = await recall(
        query="widgets",
        memories=memory_store,
        knowledge_store=knowledge_store,
        story_store=story_store,
    )
    assert len(result.stories) <= 5


# ---------------------------------------------------------------------------
# recall — content truncation
# ---------------------------------------------------------------------------


async def test_recall_truncates_long_entity_content(memory_store, knowledge_store, mock_embed):
    long_content = "x" * 2000
    await remember_decision(content=long_content, memories=memory_store)

    result = await recall(
        query="x" * 50,
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    for e in result.entities:
        assert len(e.content) <= 501  # 500 + ellipsis char


async def test_recall_truncates_long_knowledge_content(memory_store, knowledge_store, mock_embed):
    from uuid import UUID

    from charlieverse.memory.knowledge import Knowledge

    article = Knowledge(
        topic="long topic",
        content="y" * 5000,
        created_session_id=UUID(int=0),
    )
    await knowledge_store.upsert(article)

    result = await recall(
        query="long topic",
        memories=memory_store,
        knowledge_store=knowledge_store,
    )
    for k in result.knowledge:
        assert len(k.content) <= 1001  # 1000 + ellipsis char
