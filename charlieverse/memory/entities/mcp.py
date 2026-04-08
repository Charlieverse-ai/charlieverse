"""Memory tools — remember, recall, forget, pin entities."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext
from pydantic import BaseModel

from charlieverse.embeddings import encode_one, prepare_entity_text
from charlieverse.embeddings.tasks import fire_and_forget_embedding
from charlieverse.helpers.tasks import track_task
from charlieverse.memory.entities import DeleteEntity, Entity, EntityId, EntityStore, EntityType, NewEntity, UpdateEntity
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import ModelListResponse
from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.server.responses.summaries import EntitySummary, KnowledgeSummary, StorySummary
from charlieverse.types.dates import utc_now
from charlieverse.types.id import ModelId
from charlieverse.types.lists import TagList
from charlieverse.types.strings import ShortDescription, ShortString, VeryShortString

server = FastMCP(name="Memories")


# Max characters per item in recall results to prevent overwhelming responses.
_MAX_ENTITY_CONTENT = 300
_MAX_KNOWLEDGE_CONTENT = 500
_MAX_STORY_CONTENT = 300
_MAX_MESSAGE_CONTENT = 300


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
    fts_ids: set[ModelId],
    vec_ids: set[ModelId],
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
        uid = e.id
        in_fts = uid in fts_ids
        in_vec = uid in vec_ids
        relevance = 1.0 if in_fts and in_vec else 0.5

        # Recency: half-life of 14 days (2 weeks old = 0.5, 4 weeks = 0.25)
        days_old = max((now - e.updated_at).total_seconds() / 86400, 0)
        recency = math.exp(-0.693 * days_old / 14)  # ln(2) ≈ 0.693

        return (1 - recency_weight) * relevance + recency_weight * recency

    return sorted(entities, key=score, reverse=True)


def _to_summary(e: Entity) -> EntitySummary:
    from charlieverse.helpers.time_utils import relative_date

    content, truncated = _truncate(e.content, _MAX_ENTITY_CONTENT)
    return EntitySummary(
        id=e.id,
        type=e.type.value,
        content=content,
        age=relative_date(e.created_at),
        truncated=truncated,
    )


async def _fire_and_forget_embedding(memories: EntityStore, entity: Entity) -> None:
    """Generate and store embedding in background. Best-effort, never fails the caller."""
    text = prepare_entity_text(entity.content, entity.tags)
    await fire_and_forget_embedding(text, lambda emb: memories.upsert_embedding(entity.id, emb))


async def _remember(
    ctx: Context,
    *,
    type: EntityType,
    content: ShortDescription,
    session_id: SessionId,
    tags: TagList,
    pinned: bool,
) -> PermalinkResponse:
    """Shared create-and-embed flow for all remember_* helpers."""
    memories = Stores.from_context(ctx).memories

    entity = await memories.create(
        NewEntity(
            type=type,
            content=content,
            tags=tags,
            pinned=pinned,
            created_session_id=session_id,
        )
    )
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, entity)))
    return PermalinkResponse("memories", entity.id)


@server.tool
async def remember_decision(
    content: ShortString,
    rationale: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a decision and why it was made."""
    full_content = f"{content}\nRationale: {rationale}" if rationale else content
    return await _remember(
        ctx,
        type=EntityType.decision,
        content=full_content,
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_solution(
    problem: ShortString,
    solution: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a problem and how it was solved."""
    return await _remember(
        ctx,
        type=EntityType.solution,
        content=f"Problem: {problem}\nSolution: {solution}",
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_preference(
    content: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a user preference or working style note."""
    return await _remember(
        ctx,
        type=EntityType.preference,
        content=content,
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_person(
    content: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a person — who they are, relationship, context."""
    return await _remember(
        ctx,
        type=EntityType.person,
        content=content,
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_milestone(
    milestone: ShortString,
    significance: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a significant achievement or moment."""
    content = f"{milestone}\nSignificance: {significance}" if significance else milestone
    return await _remember(
        ctx,
        type=EntityType.milestone,
        content=content,
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_moment(
    moment: ShortString,
    feeling: ShortString,
    context: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a moment from our interactions."""
    parts = [moment]
    if feeling:
        parts.append(f"Feeling: {feeling}")
    if context:
        parts.append(f"Context: {context}")

    return await _remember(
        ctx,
        type=EntityType.moment,
        content="\n".join(parts),
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_project(
    name: ShortString,
    details: ShortString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember a project — name, details, what it is."""
    content = f"{name}\n{details}" if details else name
    return await _remember(
        ctx,
        type=EntityType.project,
        content=content,
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def remember_event(
    what: VeryShortString,
    when: VeryShortString,
    session_id: SessionId,
    tags: TagList,
    who: VeryShortString | None = None,
    where: VeryShortString | None = None,
    why: VeryShortString | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Remember an event — something that happened or is happening."""
    parts = [f"What: {what}", f"When: {when}"]
    if who:
        parts.append(f"Who: {who}")
    if where:
        parts.append(f"Where: {where}")
    if why:
        parts.append(f"Why: {why}")

    return await _remember(
        ctx,
        type=EntityType.event,
        content="\n".join(parts),
        session_id=session_id,
        tags=tags,
        pinned=pinned,
    )


@server.tool
async def recall(
    query: ShortString,
    limit: int = 10,
    type: str | None = None,
    ctx: Context = CurrentContext(),
) -> ModelListResponse:
    """Search across entities, knowledge, stories, and messages. Results are relevance-ordered."""
    stores = Stores.from_context(ctx)
    memories = stores.memories
    knowledge = stores.knowledge
    stories = stores.stories

    entity_type = EntityType(type) if type else None

    # FTS search entities
    if entity_type:
        entities = await memories.search(query, limit=limit)
        entities = [e for e in entities if e.type == entity_type]
    else:
        entities = await memories.search(query, limit=limit)

    # Also search knowledge
    knowledge_results = await knowledge.search(query, limit=limit)

    # Try vector search for entities too
    vector_entities: list[Entity] = []
    try:
        embedding = await encode_one(query)
        vector_entities = await memories.search_by_vector(embedding, limit=limit)
    except Exception:
        pass

    # Merge and deduplicate entities, tracking which sources found each
    fts_ids: set[ModelId] = {e.id for e in entities}
    vec_ids: set[ModelId] = {e.id for e in vector_entities}
    seen_ids: set[ModelId] = set()

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
    if stories:
        with suppress(Exception):
            story_results = await stories.search(query, limit=min(limit, 5))

    # Search messages
    messages = await stores.messages.search(query=query, limit=3)

    # Build knowledge summaries with truncation tracking
    knowledge_summaries = []
    for k in knowledge_results:
        content, truncated = _truncate(k.content, _MAX_KNOWLEDGE_CONTENT)
        knowledge_summaries.append(
            KnowledgeSummary(
                id=k.id,
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
                id=s.id,
                title=s.title,
                tier=s.tier.value,
                summary=summary_text,
                truncated=truncated,
            )
        )

    result: list[BaseModel] = [
        *[_to_summary(e) for e in merged_entities[:limit]],
        *knowledge_summaries,
        *story_summaries,
        *messages,
    ]

    return ModelListResponse(result)


@server.tool
async def update_memory(
    id: EntityId,
    session_id: SessionId,
    content: ShortDescription,
    tags: TagList,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Update an existing memory's content and/or tags. Preserves creation date and provenance."""
    memories = Stores.from_context(ctx).memories
    existing = await memories.get(id)
    if not existing:
        raise ToolError(f"Entity {id} not found")

    updated = await memories.update(
        UpdateEntity(
            id=id,
            content=content,
            tags=TagList(tags) if tags else None,
            updated_session_id=session_id,
        )
    )
    track_task(asyncio.create_task(_fire_and_forget_embedding(memories, updated)))

    return PermalinkResponse("memories", updated.id)


@server.tool
async def forget_memory(
    id: EntityId,
    ctx: Context = CurrentContext(),
) -> None:
    """Forget a memory."""
    memories = Stores.from_context(ctx).memories
    await memories.delete(DeleteEntity(id=id))


@server.tool
async def pin(
    id: ModelId,
    pinned: bool,
    ctx: Context = CurrentContext(),
) -> None:
    """Pin or unpin an entity or knowledge article."""
    stores = Stores.from_context(ctx)
    memories = stores.memories
    knowledge = stores.knowledge

    # Try entity first
    entity_id = EntityId(id)
    entity = await memories.get(entity_id)
    if entity:
        await memories.pin(entity_id, pinned)
        return

    # Try knowledge
    if knowledge:
        from charlieverse.memory.knowledge import KnowledgeId

        knowledge_id = KnowledgeId(id)
        article = await knowledge.get(knowledge_id)
        if article:
            await knowledge.pin(knowledge_id, pinned)
            return

    raise ToolError(f"No entity or knowledge article found with id {id}")
