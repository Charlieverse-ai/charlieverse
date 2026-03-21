"""Knowledge tools — search_knowledge, update_knowledge."""

from __future__ import annotations

import asyncio
from uuid import UUID

from charlieverse.db.stores import KnowledgeStore
from charlieverse.embeddings import encode_one, prepare_knowledge_text
from charlieverse.embeddings.tasks import fire_and_forget_embedding
from charlieverse.models import Knowledge
from charlieverse.tools.responses import ExpertResponse, IdResponse, KnowledgeSummary


async def _fire_and_forget_embedding(knowledge_store: KnowledgeStore, knowledge: Knowledge) -> None:
    """Generate and store embedding in background."""
    text = prepare_knowledge_text(knowledge.topic, knowledge.content, knowledge.tags)
    await fire_and_forget_embedding(text, lambda emb: knowledge_store.upsert_embedding(knowledge.id, emb))


async def search_knowledge(
    query: str,
    limit: int = 5,
    *,
    knowledge_store: KnowledgeStore,
) -> ExpertResponse:
    """Search the knowledge base. Semantic + full-text search."""
    # FTS search
    fts_results = await knowledge_store.search(query, limit=limit)

    # Vector search
    vector_results: list[Knowledge] = []
    try:
        embedding = await encode_one(query)
        vector_results = await knowledge_store.search_by_vector(embedding, limit=limit)
    except Exception:
        pass

    # Merge and deduplicate
    seen: set[UUID] = set()
    merged: list[Knowledge] = []
    for k in fts_results + vector_results:
        if k.id not in seen:
            seen.add(k.id)
            merged.append(k)

    return ExpertResponse(
        articles=[
            KnowledgeSummary(
                id=k.id, topic=k.topic, content=k.content,
                tags=k.tags, pinned=k.pinned,
            )
            for k in merged[:limit]
        ],
    )


async def update_knowledge(
    topic: str,
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    *,
    knowledge_store: KnowledgeStore,
) -> IdResponse:
    """Create or update a knowledge article."""
    knowledge = Knowledge(
        topic=topic,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
        updated_session_id=UUID(session_id) if session_id else None,
    )
    result = await knowledge_store.upsert(knowledge)
    asyncio.create_task(_fire_and_forget_embedding(knowledge_store, result))
    return IdResponse(id=result.id)
