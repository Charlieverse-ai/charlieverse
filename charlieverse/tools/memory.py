"""Memory tools — remember, recall, forget, pin entities."""

from __future__ import annotations

import asyncio
from uuid import UUID

from charlieverse.db.stores import KnowledgeStore, MemoryStore
from charlieverse.embeddings import encode_one, prepare_entity_text
from charlieverse.embeddings.tasks import fire_and_forget_embedding
from charlieverse.models import Entity, EntityType
from charlieverse.tools.responses import (
    AckResponse,
    EntitySummary,
    IdResponse,
    KnowledgeSummary,
    RecallResponse,
)


def _to_summary(e: Entity) -> EntitySummary:
    return EntitySummary(
        id=e.id,
        type=e.type.value,
        content=e.content,
        tags=e.tags,
        pinned=e.pinned,
        created_at=e.created_at,
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
    return IdResponse(id=entity.id)


async def recall(
    query: str,
    limit: int = 10,
    type: str | None = None,
    *,
    memories: MemoryStore,
    knowledge_store: KnowledgeStore,
    db=None,
) -> RecallResponse:
    """Search across entities and knowledge. Results are relevance-ordered."""
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

    # Merge and deduplicate
    seen_ids: set[UUID] = set()
    merged_entities: list[Entity] = []
    for e in entities + vector_entities:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            if entity_type and e.type != entity_type:
                continue
            merged_entities.append(e)

    # Search messages if db is available
    from charlieverse.tools.responses.recall_response import MessageSummary
    from charlieverse.db.fts import sanitize_fts_query

    message_results: list[MessageSummary] = []
    if db:
        try:
            fts_query = sanitize_fts_query(query)
            cursor = await db.execute(
                """SELECT m.id, m.role, m.content, m.created_at FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   WHERE messages_fts MATCH ?
                   ORDER BY bm25(messages_fts) LIMIT ?""",
                (fts_query, min(limit, 5)),
            )
            rows = await cursor.fetchall()
            message_results = [
                MessageSummary(
                    id=row["id"], role=row["role"],
                    content=row["content"][:500], created_at=row["created_at"],
                )
                for row in rows
            ]
        except Exception:
            pass

    return RecallResponse(
        entities=[_to_summary(e) for e in merged_entities[:limit]],
        knowledge=[
            KnowledgeSummary(
                id=k.id, topic=k.topic, content=k.content,
                tags=k.tags, pinned=k.pinned,
            )
            for k in knowledge_results
        ],
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
    asyncio.create_task(_fire_and_forget_embedding(memories, entity))
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
) -> AckResponse:
    """Pin or unpin an entity."""
    await memories.pin(UUID(id), pinned)
    return AckResponse()
