"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from contextlib import suppress

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.embeddings import encode_one
from charlieverse.memory.knowledge import (
    DeleteKnowledge,
    KnowledgeId,
    KnowledgeStore,
    NewKnowledge,
    UpdateKnowledge,
)
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import (
    CreatedResponse,
    DeletedResponse,
    ExceptionResponse,
    ModelListResponse,
    ModelResponse,
    NotFoundResponse,
)
from charlieverse.types.dates import utc_now


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register entity/knowledge/session REST endpoints on the given FastMCP instance."""

    @mcp.custom_route("/api/knowledge", methods=["GET"])
    async def api_list_knowledge(request: Request) -> ModelListResponse | ExceptionResponse:
        """List knowledge articles."""
        try:
            knowledge: KnowledgeStore = rest_stores.knowledge
            limit = int(request.query_params.get("limit", "50"))

            articles = await knowledge.fetch(limit=limit)
            return ModelListResponse(articles)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/knowledge/{id}", methods=["GET"])
    async def api_get_knowledge(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Get a single knowledge article by ID."""
        try:
            knowledge: KnowledgeStore = rest_stores.knowledge
            knowledge_id = KnowledgeId(request.path_params.get("id"))

            article = await knowledge.get(knowledge_id)
            if not article:
                return NotFoundResponse("Knowledge")

            return ModelResponse(article)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/knowledge", methods=["POST"])
    async def api_create_knowledge(request: Request) -> CreatedResponse | ExceptionResponse:
        """Create a new knowledge article."""
        try:
            body = await request.json()
            knowledge_store: KnowledgeStore = rest_stores.knowledge

            created = await knowledge_store.create(
                NewKnowledge(
                    topic=body["topic"],
                    content=body["content"],
                    tags=body.get("tags"),
                    pinned=body.get("pinned", False),
                    created_session_id=SessionId(body.get("session_id")),
                )
            )

            with suppress(Exception):
                embedding = await encode_one(f"{created.topic} {created.content}")
                await knowledge_store.upsert_embedding(created.id, embedding)

            return CreatedResponse(created)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/knowledge/{id}", methods=["PATCH"])
    async def api_update_knowledge(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Update a knowledge article's topic, content, tags, or pinned status."""
        try:
            knowledge_store: KnowledgeStore = rest_stores.knowledge
            knowledge_id = KnowledgeId(request.path_params.get("id"))
            body = await request.json()

            article = await knowledge_store.get(knowledge_id)
            if not article:
                return NotFoundResponse("Knowledge")

            updated = await knowledge_store.update(
                UpdateKnowledge(
                    id=knowledge_id,
                    topic=body.get("topic"),
                    content=body.get("content"),
                    tags=body.get("tags"),
                    pinned=body.get("pinned"),
                    updated_at=utc_now(),
                )
            )

            if "topic" in body or "content" in body:
                with suppress(Exception):
                    embedding = await encode_one(f"{updated.topic} {updated.content}")
                    await knowledge_store.upsert_embedding(updated.id, embedding)

            return ModelResponse(updated)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/knowledge/{id}", methods=["DELETE"])
    async def api_delete_knowledge(request: Request) -> DeletedResponse | NotFoundResponse | ExceptionResponse:
        """Delete a knowledge article."""
        try:
            knowledge_store: KnowledgeStore = rest_stores.knowledge
            knowledge_id = KnowledgeId(request.path_params.get("id"))

            article = await knowledge_store.get(knowledge_id)
            if not article:
                return NotFoundResponse("Knowledge")

            await knowledge_store.delete(DeleteKnowledge(id=knowledge_id))
            return DeletedResponse()
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/knowledge/{id}/pin", methods=["POST"])
    async def api_pin_knowledge(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Toggle pin status on a knowledge article."""
        try:
            knowledge_store: KnowledgeStore = rest_stores.knowledge
            knowledge_id = KnowledgeId(request.path_params.get("id"))
            body = await request.json()

            article = await knowledge_store.get(knowledge_id)
            if not article:
                return NotFoundResponse("Knowledge")

            pinned = body.get("pinned", not article.pinned)
            await knowledge_store.pin(knowledge_id, pinned)
            article.pinned = pinned

            return ModelResponse(article)
        except Exception as e:
            return ExceptionResponse(e)
