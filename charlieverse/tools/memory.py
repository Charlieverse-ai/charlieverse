"""Memory tools — remember, recall, forget, pin entities."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from uuid import UUID

from charlieverse.db.stores import MemoryStore
from charlieverse.embeddings import encode_one, prepare_entity_text
from charlieverse.embeddings.tasks import fire_and_forget_embedding
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.stories import StoryStore
from charlieverse.models import Entity, EntityType
from charlieverse.tasks import track_task
from charlieverse.tools.responses import (
    AckResponse,
    EntitySummary,
    IdResponse,
    KnowledgeSummary,
    RecallResponse,
    StorySummary,
)
from charlieverse.types.dates import from_iso, utc_now


def _to_summary(e: Entity) -> EntitySummary:
    from charlieverse.context.time_utils import relative_date

    content, truncated = _truncate(e.content, _MAX_ENTITY_CONTENT)
    return EntitySummary(
        id=e.id,
        type=e.type.value,
        content=content,
        age=relative_date(e.created_at),
        truncated=truncated,
    )


async def _fire_and_forget_embedding(memories: MemoryStore, entity: Entity) -> None:
    """Generate and store embedding in background. Best-effort, never fails the caller."""
    text = prepare_entity_text(entity.content, entity.tags)
    await fire_and_forget_embedding(text, lambda emb: memories.upsert_embedding(entity.id, emb))


async def remember_decision(
    content: str,
    rationale: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a decision and why it was made."""
    full_content = content
    if rationale:
        full_content = f"{content}\nRationale: {rationale}"

    entity = Entity(
        type=EntityType.decision,
        content=full_content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_solution(
    problem: str,
    solution: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a problem and how it was solved."""
    content = f"Problem: {problem}\nSolution: {solution}"
    entity = Entity(
        type=EntityType.solution,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_preference(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a user preference or working style note."""
    entity = Entity(
        type=EntityType.preference,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_person(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a person — who they are, relationship, context."""
    entity = Entity(
        type=EntityType.person,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_milestone(
    milestone: str,
    significance: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a significant achievement or moment."""
    content = milestone
    if significance:
        content = f"{milestone}\nSignificance: {significance}"

    entity = Entity(
        type=EntityType.milestone,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_moment(
    moment: str,
    feeling: str | None = None,
    context: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a moment from our interactions."""
    parts = [moment]
    if feeling:
        parts.append(f"Feeling: {feeling}")
    if context:
        parts.append(f"Context: {context}")

    entity = Entity(
        type=EntityType.moment,
        content="\n".join(parts),
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_project(
    name: str,
    details: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember a project — name, details, what it is."""
    content = name
    if details:
        content = f"{name}\n{details}"

    entity = Entity(
        type=EntityType.project,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


async def remember_event(
    what: str,
    when: str,
    who: str | None = None,
    where: str | None = None,
    why: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    memories: MemoryStore,
) -> IdResponse:
    """Remember an event — something that happened or is happening."""
    parts = [f"What: {what}", f"When: {when}"]
    if who:
        parts.append(f"Who: {who}")
    if where:
        parts.append(f"Where: {where}")
    if why:
        parts.append(f"Why: {why}")

    entity = Entity(
        type=EntityType.event,
        content="\n".join(parts),
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entity = await memories.create(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return IdResponse(id=entity.id)


# Max characters per item in recall results to prevent overwhelming responses.
_MAX_ENTITY_CONTENT = 500
_MAX_KNOWLEDGE_CONTENT = 1000
_MAX_STORY_CONTENT = 500
_MAX_MESSAGE_CONTENT = 500


def _truncate(text: str, max_len: int, *, plaintext: bool = True) -> tuple[str, bool]:
    """Truncate text to max_len, appending '…' if trimmed. Returns (text, was_truncated).

    If plaintext=True (default), strips markdown formatting first for denser content.
    """
    from charlieverse.nlp.markdown import strip_markdown

    s = strip_markdown(text) if plaintext else text
    if len(s) <= max_len:
        return s, False
    return s[:max_len] + "…", True


def _rank_by_relevance_and_recency(
    entities: list[Entity],
    fts_ids: set[UUID],
    vec_ids: set[UUID],
    recency_weight: float = 0.4,
) -> list[Entity]:
    """Re-rank entities by combined relevance and recency.

    Relevance: 1.0 if found by both FTS+vector, 0.5 if found by one.
    Recency: exponential decay based on days since updated_at.
    Final score = (1 - recency_weight) * relevance + recency_weight * recency.
    """
    import math

    now = utc_now()

    def score(e: Entity) -> float:
        # Relevance: both sources = 1.0, one source = 0.5
        in_fts = e.id in fts_ids
        in_vec = e.id in vec_ids
        relevance = 1.0 if in_fts and in_vec else 0.5

        # Recency: half-life of 14 days (2 weeks old = 0.5, 4 weeks = 0.25)
        days_old = max((now - e.updated_at).total_seconds() / 86400, 0)
        recency = math.exp(-0.693 * days_old / 14)  # ln(2) ≈ 0.693

        return (1 - recency_weight) * relevance + recency_weight * recency

    return sorted(entities, key=score, reverse=True)


async def recall(
    query: str,
    limit: int = 10,
    type: str | None = None,
    *,
    memories: MemoryStore,
    knowledge_store: KnowledgeStore,
    story_store: StoryStore | None = None,
    db=None,
) -> RecallResponse:
    """Search across entities, knowledge, stories, and messages. Results are relevance-ordered."""
    entity_type = EntityType(type) if type else None

    # FTS search entities
    if entity_type:
        entities = await memories.search(query, limit=limit)
        entities = [e for e in entities if e.type == entity_type]
    else:
        entities = await memories.search(query, limit=limit)

    # Also search knowledge
    knowledge_results = await knowledge_store.search(query, limit=limit)

    # Try vector search for entities too
    vector_entities: list[Entity] = []
    try:
        embedding = await encode_one(query)
        vector_entities = await memories.search_by_vector(embedding, limit=limit)
    except Exception:
        pass

    # Merge and deduplicate entities, tracking which sources found each
    fts_ids = {e.id for e in entities}
    vec_ids = {e.id for e in vector_entities}
    seen_ids: set[UUID] = set()
    merged_entities: list[Entity] = []
    for e in entities + vector_entities:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            if entity_type and e.type != entity_type:
                continue
            merged_entities.append(e)

    # Re-sort by combined relevance + recency score
    merged_entities = _rank_by_relevance_and_recency(
        merged_entities,
        fts_ids,
        vec_ids,
    )

    # Search stories
    from charlieverse.memory.stories import Story

    story_results: list[Story] = []
    if story_store:
        with suppress(Exception):
            story_results = await story_store.search(query, limit=min(limit, 5))

    # Search messages if db is available
    from charlieverse.context.time_utils import relative_date
    from charlieverse.db.fts import sanitize_fts_query
    from charlieverse.tools.responses.recall_response import MessageSummary

    # Junk patterns to filter out of message search results
    _junk_prefixes = (
        "<task-notification>",
        "<command-name>",
        "<local-command",
        "<system-reminder>",
    )

    message_results: list[MessageSummary] = []
    if db:
        try:
            fts_query = sanitize_fts_query(query)
            if fts_query:
                # Fetch extra to account for junk filtering
                cursor = await db.execute(
                    """SELECT m.id, m.role, m.content, m.created_at FROM messages m
                       JOIN messages_fts fts ON m.rowid = fts.rowid
                       WHERE messages_fts MATCH ?
                       ORDER BY bm25(messages_fts) LIMIT ?""",
                    (fts_query, min(limit, 5) * 3),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    if len(message_results) >= min(limit, 5):
                        break
                    content = row["content"].strip()
                    if any(content.startswith(p) for p in _junk_prefixes):
                        continue
                    try:
                        age = relative_date(from_iso(row["created_at"]))
                    except (ValueError, TypeError):
                        age = row["created_at"]
                    message_results.append(
                        MessageSummary(
                            id=row["id"],
                            role=row["role"],
                            content=_truncate(content, _MAX_MESSAGE_CONTENT)[0],
                            age=age,
                        )
                    )
        except Exception:
            pass

    # Build knowledge summaries with truncation tracking
    knowledge_summaries = []
    for k in knowledge_results:
        content, truncated = _truncate(k.content, _MAX_KNOWLEDGE_CONTENT)
        knowledge_summaries.append(
            KnowledgeSummary(
                id=k.id.uuid,
                content=content,
                truncated=truncated,
            )
        )

    # Build story summaries — prefer summary field, fall back to truncated content
    story_summaries = []
    for s in story_results:
        if s.summary:
            summary_text, truncated = s.summary, False
        else:
            summary_text, truncated = _truncate(s.content, _MAX_STORY_CONTENT)
        story_summaries.append(
            StorySummary(
                id=str(s.id),
                title=s.title,
                tier=s.tier.value,
                summary=summary_text,
                truncated=truncated,
            )
        )

    return RecallResponse(
        entities=[_to_summary(e) for e in merged_entities[:limit]],
        knowledge=knowledge_summaries,
        stories=story_summaries,
        messages=message_results,
    )


async def update_memory(
    id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    session_id: str | None = None,
    *,
    memories: MemoryStore,
) -> AckResponse:
    """Update an existing memory's content and/or tags. Preserves creation date and provenance."""
    entity = await memories.get(UUID(id))
    if not entity:
        from fastmcp.exceptions import ToolError

        raise ToolError(f"Entity {id} not found")

    if content is not None:
        entity.content = content
    if tags is not None:
        entity.tags = tags
    if session_id:
        entity.updated_session_id = UUID(session_id)

    await memories.update(entity)
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return AckResponse()


async def forget(
    id: str,
    *,
    memories: MemoryStore,
) -> AckResponse:
    """Soft-delete an entity."""
    await memories.delete(UUID(id))
    return AckResponse()


async def pin(
    id: str,
    pinned: bool,
    *,
    memories: MemoryStore,
    knowledge_store: KnowledgeStore | None = None,
) -> AckResponse:
    """Pin or unpin an entity or knowledge article."""
    uid = UUID(id)

    # Try entity first
    entity = await memories.get(uid)
    if entity:
        await memories.pin(uid, pinned)
        return AckResponse()

    # Try knowledge
    if knowledge_store:
        from charlieverse.memory.knowledge import KnowledgeId

        knowledge_id = KnowledgeId(uid)
        article = await knowledge_store.get(knowledge_id)
        if article:
            await knowledge_store.pin(knowledge_id, pinned)
            return AckResponse()

    raise ValueError(f"No entity or knowledge article found with id {id}")
