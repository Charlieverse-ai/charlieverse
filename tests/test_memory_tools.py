"""Tests for the memory tool functions (called directly, not via FastMCP)."""

from __future__ import annotations

import pytest

from charlieverse.tools.memory import (
    forget,
    pin,
    remember_decision,
    remember_milestone,
    remember_moment,
    remember_person,
    remember_preference,
    remember_solution,
    update_memory,
)
from charlieverse.tools.responses import IdResponse


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
    from charlieverse.models import EntityType
    from charlieverse.db.stores import MemoryStore
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
