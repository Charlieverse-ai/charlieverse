"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from contextlib import suppress

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.api.responses import (
    CreatedResponse,
    DeletedResponse,
    ExceptionResponse,
    ModelListResponse,
    ModelResponse,
    NotFoundResponse,
    SearchResults,
    Stats,
)
from charlieverse.db.fts import clean_text
from charlieverse.embeddings import encode_one
from charlieverse.memory.entities import (
    DeleteEntity,
    EntityId,
    EntityStore,
    EntityType,
    NewEntity,
    UpdateEntity,
)
from charlieverse.memory.knowledge import (
    DeleteKnowledge,
    KnowledgeId,
    KnowledgeStore,
    NewKnowledge,
    UpdateKnowledge,
)
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.types.dates import utc_now


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register entity/knowledge/session REST endpoints on the given FastMCP instance."""

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/memories", methods=["GET"])
    async def api_list_entities(request: Request) -> ModelListResponse | ExceptionResponse:
        """List entities, optionally filtered by type."""
        try:
            memories: EntityStore = rest_stores.memories
            type_param = request.query_params.get("type")
            limit = int(request.query_params.get("limit", "100"))

            entity_type = EntityType(type_param) if type_param else None
            entities = await memories.list(entity_type=entity_type, limit=limit)

            return ModelListResponse(entities)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/memories/{id}", methods=["GET"])
    async def api_get_entity(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Get a single entity by ID."""
        try:
            memories: EntityStore = rest_stores.memories
            entity_id = EntityId(request.path_params.get("id"))

            entity = await memories.get(entity_id)
            if not entity:
                return NotFoundResponse("Memory")

            return ModelResponse(entity)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/memories", methods=["POST"])
    async def api_create_entity(request: Request) -> CreatedResponse | ExceptionResponse:
        """Create a new entity."""
        try:
            body = await request.json()
            memories: EntityStore = rest_stores.memories

            created = await memories.create(
                NewEntity(
                    type=EntityType(body["type"]),
                    content=body["content"],
                    tags=body.get("tags"),
                    pinned=body.get("pinned", False),
                    created_session_id=SessionId(body.get("session_id")),
                )
            )

            with suppress(Exception):
                embedding = await encode_one(created.content)
                await memories.upsert_embedding(created.id, embedding)

            return CreatedResponse(created)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/memories/{id}", methods=["PATCH"])
    async def api_update_entity(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Update an entity's content, tags, or pinned status."""
        try:
            memories: EntityStore = rest_stores.memories
            entity_id = EntityId(request.path_params.get("id"))
            body = await request.json()

            entity = await memories.get(entity_id)
            if not entity:
                return NotFoundResponse("Memory")

            updated = await memories.update(
                UpdateEntity(
                    id=entity_id,
                    content=body.get("content"),
                    tags=body.get("tags"),
                    pinned=body.get("pinned"),
                    updated_at=utc_now(),
                )
            )

            if "content" in body:
                with suppress(Exception):
                    embedding = await encode_one(updated.content)
                    await memories.upsert_embedding(updated.id, embedding)

            return ModelResponse(updated)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/memories/{id}", methods=["DELETE"])
    async def api_delete_entity(request: Request) -> DeletedResponse | NotFoundResponse | ExceptionResponse:
        """Soft-delete an entity."""
        try:
            memories: EntityStore = rest_stores.memories
            entity_id = EntityId(request.path_params.get("id"))

            entity = await memories.get(entity_id)
            if not entity:
                return NotFoundResponse("Memory")

            await memories.delete(DeleteEntity(id=entity_id))
            return DeletedResponse()
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/memories/{id}/pin", methods=["POST"])
    async def api_pin_entity(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Toggle pin status on an entity."""
        try:
            memories: EntityStore = rest_stores.memories
            entity_id = EntityId(request.path_params.get("id"))
            body = await request.json()

            entity = await memories.get(entity_id)
            if not entity:
                return NotFoundResponse("Memory")

            pinned = body.get("pinned", not entity.pinned)
            await memories.pin(entity_id, pinned)
            entity.pinned = pinned

            return ModelResponse(entity)
        except Exception as e:
            return ExceptionResponse(e)

    # ------------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/knowledge", methods=["GET"])
    async def api_list_knowledge(request: Request) -> ModelListResponse | ExceptionResponse:
        """List knowledge articles."""
        try:
            knowledge: KnowledgeStore = rest_stores.knowledge
            limit = int(request.query_params.get("limit", "50"))

            articles = await knowledge.list(limit=limit)
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

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/sessions/list", methods=["GET"])
    async def api_list_sessions(request: Request) -> ModelListResponse | ExceptionResponse:
        """List recent sessions."""
        try:
            store: SessionStore = rest_stores.sessions
            limit = int(request.query_params.get("limit", "50"))

            sessions = await store.recent(limit=limit)
            return ModelListResponse(sessions)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/sessions/{id}", methods=["GET"])
    async def api_get_session(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Get a single session by ID."""
        try:
            sessions: SessionStore = rest_stores.sessions
            session_id = SessionId(request.path_params["id"])
            session = await sessions.get(session_id)

            if not session:
                return NotFoundResponse("Session")

            return ModelResponse(session)
        except Exception as e:
            return ExceptionResponse(e)

    # ------------------------------------------------------------------
    # Search + stats
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/search", methods=["POST"])
    async def api_search(request: Request) -> ModelResponse | ExceptionResponse:
        """Unified search — FTS5 with prefix matching, vector fallback."""
        try:
            body = await request.json()
            query = clean_text(body.get("query", ""))
            limit = body.get("limit", 10)

            if not query:
                return ModelResponse(SearchResults(memories=[], knowledge=[]))

            memories: EntityStore = rest_stores.memories
            knowledge: KnowledgeStore = rest_stores.knowledge

            entity_results = await memories.search(query, limit=limit)
            knowledge_results = await knowledge.search(query, limit=limit)

            if not entity_results and not knowledge_results:
                embedding = await encode_one(query)
                entity_results = await memories.search_by_vector(embedding, limit=limit)
                knowledge_results = await knowledge.search_by_vector(embedding, limit=limit)

            return ModelResponse(SearchResults(memories=entity_results, knowledge=knowledge_results))
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/stats", methods=["GET"])
    async def api_stats(request: Request) -> ModelResponse | ExceptionResponse:
        """Dashboard stats — entity counts by type, session count, knowledge count."""
        try:
            memories: EntityStore = rest_stores.memories
            sessions_store: SessionStore = rest_stores.sessions
            knowledge: KnowledgeStore = rest_stores.knowledge

            return ModelResponse(
                Stats(
                    entities=await memories.count_by_type(),
                    sessions=await sessions_store.count_with_summary(),
                    knowledge=await knowledge.count(),
                )
            )
        except Exception as e:
            return ExceptionResponse(e)
