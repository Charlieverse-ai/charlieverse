"""CRUD and search tests for EntityStore."""

from __future__ import annotations

from uuid import UUID

from charlieverse.memory.entities import (
    DeleteEntity,
    EntityId,
    EntityType,
    NewEntity,
    UpdateEntity,
)
from charlieverse.memory.sessions import SessionId
from charlieverse.types.lists import TagList

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = SessionId(UUID(int=0))


def _new(content: str, type: EntityType = EntityType.decision, **kw) -> NewEntity:
    return NewEntity(
        type=type,
        content=content,
        tags=kw.pop("tags", ["test"]),
        created_session_id=_SESSION,
        **kw,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_entity(memory_store):
    entity = await memory_store.create(_new("use pytest"))
    assert entity.id is not None
    assert isinstance(entity.id, EntityId)


async def test_create_stores_content(memory_store):
    e = await memory_store.create(_new("store this content"))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.content == "store this content"


async def test_create_stores_tags(memory_store):
    e = await memory_store.create(_new("tagged entity", tags=["pytest", "testing"]))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.tags == ["pytest", "testing"]


async def test_create_stores_type(memory_store):
    e = await memory_store.create(_new("a preference", type=EntityType.preference))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.type == EntityType.preference


# ---------------------------------------------------------------------------
# Get / list
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(memory_store):
    result = await memory_store.get(EntityId())
    assert result is None


async def test_list_returns_all_active(memory_store):
    await memory_store.create(_new("entity one"))
    await memory_store.create(_new("entity two"))
    results = await memory_store.fetch()
    assert len(results) >= 2


async def test_list_filters_by_type(memory_store):
    await memory_store.create(_new("decision one", type=EntityType.decision))
    await memory_store.create(_new("preference one", type=EntityType.preference))
    decisions = await memory_store.fetch(entity_type=EntityType.decision)
    for e in decisions:
        assert e.type == EntityType.decision


# ---------------------------------------------------------------------------
# Search (FTS)
# ---------------------------------------------------------------------------


async def test_search_finds_entity(memory_store):
    await memory_store.create(_new("use pytest for testing"))
    await memory_store.rebuild_fts()
    results = await memory_store.search("pytest")
    assert any("pytest" in r.content.lower() for r in results)


async def test_search_empty_after_stopword_query(memory_store):
    await memory_store.create(_new("something interesting"))
    await memory_store.rebuild_fts()
    # "the" is a stopword — sanitize_fts_query returns "" — search returns []
    results = await memory_store.search("the")
    assert results == []


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(memory_store):
    e = await memory_store.create(_new("original content"))
    await memory_store.update(UpdateEntity(id=e.id, content="updated content"))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.content == "updated content"


async def test_update_changes_tags(memory_store):
    e = await memory_store.create(_new("tag test", tags=["old"]))
    await memory_store.update(UpdateEntity(id=e.id, tags=TagList(["new", "tags"])))
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.tags == ["new", "tags"]


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_entity(memory_store):
    e = await memory_store.create(_new("delete me"))
    await memory_store.delete(DeleteEntity(id=e.id))
    result = await memory_store.get(e.id)
    assert result is None


async def test_soft_deleted_excluded_from_search(memory_store):
    e = await memory_store.create(_new("unique phrase xyzzy deleted"))
    await memory_store.delete(DeleteEntity(id=e.id))
    await memory_store.rebuild_fts()
    results = await memory_store.search("xyzzy")
    assert len(results) == 0


async def test_soft_deleted_excluded_from_list(memory_store):
    e = await memory_store.create(_new("list exclusion test"))
    count_before = len(await memory_store.fetch())
    await memory_store.delete(DeleteEntity(id=e.id))
    count_after = len(await memory_store.fetch())
    assert count_after == count_before - 1


# ---------------------------------------------------------------------------
# Pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_sets_pinned_true(memory_store):
    e = await memory_store.create(_new("pin this"))
    assert not e.pinned
    await memory_store.pin(e.id, True)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.pinned is True


async def test_unpin_sets_pinned_false(memory_store):
    e = await memory_store.create(_new("unpin this", pinned=True))
    await memory_store.pin(e.id, False)
    fetched = await memory_store.get(e.id)
    assert fetched is not None
    assert fetched.pinned is False


async def test_pinned_list_returns_pinned_only(memory_store):
    await memory_store.create(_new("not pinned"))
    ep = await memory_store.create(_new("pinned one"))
    await memory_store.pin(ep.id, True)
    pinned = await memory_store.pinned()
    assert all(e.pinned for e in pinned)
    assert any(e.id == ep.id for e in pinned)


# ---------------------------------------------------------------------------
# List ordering — updated_at DESC
# ---------------------------------------------------------------------------


async def test_list_orders_by_updated_at_desc(memory_store):
    """Entities updated more recently should appear first, regardless of creation order."""
    e_first = await memory_store.create(_new("created first"))
    e_second = await memory_store.create(_new("created second"))

    await memory_store.update(UpdateEntity(id=e_first.id, content="created first — updated"))

    results = await memory_store.fetch()
    ids = [e.id for e in results]
    assert ids.index(e_first.id) < ids.index(e_second.id), "The updated entity should appear before the not-updated one"


async def test_list_filtered_by_type_orders_by_updated_at_desc(memory_store):
    """Type-filtered list also orders by updated_at DESC."""
    e_old = await memory_store.create(_new("old moment", type=EntityType.moment))
    e_new = await memory_store.create(_new("new moment", type=EntityType.moment))

    await memory_store.update(UpdateEntity(id=e_old.id, content="old moment — refreshed"))

    results = await memory_store.fetch(entity_type=EntityType.moment)
    ids = [e.id for e in results]
    assert ids.index(e_old.id) < ids.index(e_new.id), "The updated moment should appear first when filtering by type"
