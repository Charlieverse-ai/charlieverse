"""MCP tools: search_knowledge, update_knowledge."""

from __future__ import annotations

import asyncio

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.api.responses import ModelListResponse
from charlieverse.api.responses.knowledge_summary import KnowledgeSummary
from charlieverse.api.responses.permalink import PermalinkResponse
from charlieverse.embeddings import encode_one, prepare_knowledge_text
from charlieverse.embeddings.tasks import fire_and_forget_embedding
from charlieverse.mcp.context import _stores
from charlieverse.memory.knowledge import KnowledgeId
from charlieverse.memory.sessions import SessionId
from charlieverse.tasks import track_task
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString

from .models import Knowledge, NewKnowledge
from .store import KnowledgeStore

server = FastMCP(name="Knowledge")


@server.tool
async def search(
    query: NonEmptyString,
    limit: int = 5,
    ctx: Context = CurrentContext(),
) -> ModelListResponse:
    """Search the knowledge base. Semantic + full-text search across knowledge articles."""
    knowledge_store: KnowledgeStore = _stores(ctx).knowledge

    fts_results = await knowledge_store.search(query, limit=limit)

    vector_results: list[Knowledge] = []
    try:
        embedding = await encode_one(query)
        vector_results = await knowledge_store.search_by_vector(embedding, limit=limit)
    except Exception:
        pass

    seen: set[KnowledgeId] = set()
    merged: list[Knowledge] = []
    for k in fts_results + vector_results:
        key = k.id
        if key not in seen:
            seen.add(key)
            merged.append(k)

    return ModelListResponse([KnowledgeSummary(id=k.id, content=k.content) for k in merged[:limit]])


@server.tool
async def update(
    topic: NonEmptyString,
    content: NonEmptyString,
    session_id: SessionId,
    tags: TagList,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Create or update a knowledge article."""
    knowledge_store: KnowledgeStore = _stores(ctx).knowledge

    knowledge = NewKnowledge(
        topic=topic,
        content=content,
        tags=tags,
        pinned=pinned,
        created_session_id=session_id,
    )
    result = await knowledge_store.upsert(knowledge)

    async def _embed() -> None:
        text = prepare_knowledge_text(result.topic, result.content, result.tags)
        await fire_and_forget_embedding(text, lambda emb: knowledge_store.upsert_embedding(result.id, emb))

    track_task(asyncio.create_task(_embed()))

    return PermalinkResponse("knowledge", result.id)


def _raise_not_found(id_: str) -> None:
    raise ToolError(f"Knowledge article {id_!r} not found")
