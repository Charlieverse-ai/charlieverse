"""CRUD and search tests for MemoryStore."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from charlieverse.models import Entity, EntityType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = UUID(int=0)


def _entity(content: str, type: EntityType = EntityType.decision, **kw) -> Entity:
    return Entity(
        type=type,
        content=content,
        created_session_id=_SESSION,
        **kw,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_entity(memory_store):
    entity = await memory_store.create(_entity("use pytest"))
    assert entity.id is not None
    assert isinstance(entity.id, UUID)


async def test_create_stores_content(memory_store):
    e = await memory_store.create(_entity("store this content"))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.content == "store this content"


async def test_create_stores_tags(memory_store):
    e = await memory_store.create(_entity("tagged entity", tags=["pytest", "testing"]))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.tags == ["pytest", "testing"]


async def test_create_stores_type(memory_store):
    e = await memory_store.create(_entity("a preference", type=EntityType.preference))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.type == EntityType.preference


# ---------------------------------------------------------------------------
# Get / list
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(memory_store):
    result = await memory_store.get(uuid4())
    assert result is None


async def test_list_returns_all_active(memory_store):
    await memory_store.create(_entity("entity one"))
    await memory_store.create(_entity("entity two"))
    results = await memory_store.list()
    assert len(results) >= 2


async def test_list_filters_by_type(memory_store):
    await memory_store.create(_entity("decision one", type=EntityType.decision))
    await memory_store.create(_entity("preference one", type=EntityType.preference))
    decisions = await memory_store.list(entity_type=EntityType.decision)
    for e in decisions:
        assert e.type == EntityType.decision


# ---------------------------------------------------------------------------
# Search (FTS)
# ---------------------------------------------------------------------------


async def test_search_finds_entity(memory_store):
    await memory_store.create(_entity("use pytest for testing"))
    await memory_store.rebuild_fts()
    results = await memory_store.search("pytest")
    assert any("pytest" in r.content.lower() for r in results)


async def test_search_empty_after_stopword_query(memory_store):
    await memory_store.create(_entity("something interesting"))
    await memory_store.rebuild_fts()
    # "the" is a stopword — sanitize_fts_query returns "" — search returns []
    results = await memory_store.search("the")
    assert results == []


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(memory_store):
    e = await memory_store.create(_entity("original content"))
    e.content = "updated content"
    await memory_store.update(e)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.content == "updated content"


async def test_update_changes_tags(memory_store):
    e = await memory_store.create(_entity("tag test", tags=["old"]))
    e.tags = ["new", "tags"]
    await memory_store.update(e)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.tags == ["new", "tags"]


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_entity(memory_store):
    e = await memory_store.create(_entity("delete me"))
    await memory_store.delete(e.id)
    result = await memory_store.get(e.id)
    assert result is None


async def test_soft_deleted_excluded_from_search(memory_store):
    e = await memory_store.create(_entity("unique phrase xyzzy deleted"))
    await memory_store.delete(e.id)
    await memory_store.rebuild_fts()
    results = await memory_store.search("xyzzy")
    assert len(results) == 0


async def test_soft_deleted_excluded_from_list(memory_store):
    e = await memory_store.create(_entity("list exclusion test"))
    count_before = len(await memory_store.list())
    await memory_store.delete(e.id)
    count_after = len(await memory_store.list())
    assert count_after == count_before - 1


# ---------------------------------------------------------------------------
# Pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_sets_pinned_true(memory_store):
    e = await memory_store.create(_entity("pin this"))
    assert not e.pinned
    await memory_store.pin(e.id, True)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.pinned is True


async def test_unpin_sets_pinned_false(memory_store):
    e = await memory_store.create(_entity("unpin this", pinned=True))
    await memory_store.pin(e.id, False)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.pinned is False


async def test_pinned_list_returns_pinned_only(memory_store):
    await memory_store.create(_entity("not pinned"))
    ep = await memory_store.create(_entity("pinned one"))
    await memory_store.pin(ep.id, True)
    pinned = await memory_store.pinned()
    assert all(e.pinned for e in pinned)
    assert any(e.id == ep.id for e in pinned)
