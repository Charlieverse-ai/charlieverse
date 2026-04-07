"""CRUD and search tests for KnowledgeStore."""

from __future__ import annotations

from uuid import UUID, uuid4

from charlieverse.memory.knowledge import Knowledge, KnowledgeStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = UUID(int=0)


def _article(topic: str, content: str = "some knowledge", **kw) -> Knowledge:
    return Knowledge(
        topic=topic,
        content=content,
        created_session_id=_SESSION,
        **kw,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_article(knowledge_store: KnowledgeStore):
    article = await knowledge_store.create(_article("pytest basics"))
    assert article.id is not None
    assert isinstance(article.id, UUID)


async def test_create_stores_content(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("topic A", "content for topic A"))
    fetched = await knowledge_store.get(a.id)
    assert fetched is not None
    assert fetched.topic == "topic A"
    assert fetched.content == "content for topic A"


async def test_create_stores_tags(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("tagged", tags=["python", "testing"]))
    fetched = await knowledge_store.get(a.id)
    assert fetched is not None
    assert fetched.tags == ["python", "testing"]


# ---------------------------------------------------------------------------
# Get / list
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(knowledge_store: KnowledgeStore):
    result = await knowledge_store.get(uuid4())
    assert result is None


async def test_list_returns_all_active(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("article one"))
    await knowledge_store.create(_article("article two"))
    results = await knowledge_store.fetch()
    assert len(results) >= 2


async def test_find_by_topic(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("unique topic xyz"))
    found = await knowledge_store.find_by_topic("unique topic xyz")
    assert found is not None
    assert found.topic == "unique topic xyz"


async def test_find_by_topic_returns_none_for_missing(knowledge_store: KnowledgeStore):
    result = await knowledge_store.find_by_topic("nonexistent topic")
    assert result is None


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def test_upsert_creates_new(knowledge_store: KnowledgeStore):
    a = await knowledge_store.upsert(_article("new topic", "new content"))
    fetched = await knowledge_store.get(a.id)
    assert fetched is not None
    assert fetched.content == "new content"


async def test_upsert_updates_existing_by_topic(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("same topic", "original"))
    updated = await knowledge_store.upsert(_article("same topic", "updated"))
    fetched = await knowledge_store.find_by_topic("same topic")
    assert fetched is not None
    assert fetched.content == updated.content


async def test_upsert_preserves_id_on_update(knowledge_store: KnowledgeStore):
    original = await knowledge_store.create(_article("stable id topic", "v1"))
    updated = await knowledge_store.upsert(_article("stable id topic", "v2"))
    assert updated.id == original.id


# ---------------------------------------------------------------------------
# Search (FTS)
# ---------------------------------------------------------------------------


async def test_search_finds_article(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("python testing", "pytest is great for testing"))
    await knowledge_store.rebuild_fts()
    results = await knowledge_store.search("pytest")
    assert any("pytest" in r.content.lower() for r in results)


async def test_search_empty_query_returns_empty(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("something", "interesting content"))
    await knowledge_store.rebuild_fts()
    results = await knowledge_store.search("the")
    assert results == []


async def test_search_no_results_for_unrelated(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("python", "flask and django"))
    await knowledge_store.rebuild_fts()
    results = await knowledge_store.search("xyznonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_article(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("delete me"))
    await knowledge_store.delete(a.id)
    result = await knowledge_store.get(a.id)
    assert result is None


async def test_soft_deleted_excluded_from_list(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("list exclusion"))
    count_before = len(await knowledge_store.fetch())
    await knowledge_store.delete(a.id)
    count_after = len(await knowledge_store.fetch())
    assert count_after == count_before - 1


async def test_soft_deleted_excluded_from_search(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("unique xyzzy knowledge", "xyzzy content"))
    await knowledge_store.delete(a.id)
    await knowledge_store.rebuild_fts()
    results = await knowledge_store.search("xyzzy")
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Pin / unpin
# ---------------------------------------------------------------------------


async def test_pin_sets_pinned_true(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("pin this"))
    assert not a.pinned
    await knowledge_store.pin(a.id, True)
    fetched = await knowledge_store.get(a.id)
    assert fetched is not None
    assert fetched.pinned is True


async def test_unpin_sets_pinned_false(knowledge_store: KnowledgeStore):
    a = await knowledge_store.create(_article("unpin this", pinned=True))
    await knowledge_store.pin(a.id, False)
    fetched = await knowledge_store.get(a.id)
    assert fetched is not None
    assert fetched.pinned is False


async def test_pinned_list_returns_pinned_only(knowledge_store: KnowledgeStore):
    await knowledge_store.create(_article("not pinned"))
    ap = await knowledge_store.create(_article("pinned one"))
    await knowledge_store.pin(ap.id, True)
    pinned = await knowledge_store.pinned()
    assert all(a.pinned for a in pinned)
    assert any(a.id == ap.id for a in pinned)
