"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from contextlib import suppress

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.embeddings import encode_one
from charlieverse.memory.entities import (
    DeleteEntity,
    EntityId,
    EntityStore,
    EntityType,
    NewEntity,
    UpdateEntity,
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
            entities = await memories.fetch(entity_type=entity_type, limit=limit)

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
