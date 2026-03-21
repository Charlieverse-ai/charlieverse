"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore
from charlieverse.embeddings import encode_one
from charlieverse.models import Entity, EntityType, Knowledge


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_entity(entity) -> dict:
    """Convert an Entity model to a JSON-safe dict."""
    return {
        "id": str(entity.id),
        "type": entity.type.value,
        "content": entity.content,
        "tags": entity.tags,
        "pinned": entity.pinned,
        "created_session_id": str(entity.created_session_id),
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat(),
    }


def _serialize_session(session) -> dict:
    """Convert a Session model to a JSON-safe dict."""
    return {
        "id": str(session.id),
        "what_happened": session.what_happened,
        "for_next_session": session.for_next_session,
        "tags": session.tags,
        "workspace": session.workspace,
        "transcript_path": session.transcript_path,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _serialize_knowledge(article) -> dict:
    """Convert a Knowledge model to a JSON-safe dict."""
    return {
        "id": str(article.id),
        "topic": article.topic,
        "content": article.content,
        "tags": article.tags,
        "pinned": article.pinned,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register_routes(mcp: FastMCP, rest_stores: dict) -> None:
    """Register entity/knowledge/session REST endpoints on the given FastMCP instance."""

    @mcp.custom_route("/api/entities", methods=["GET"])
    async def api_list_entities(request: Request) -> JSONResponse:
        """List entities, optionally filtered by type."""
        memories: MemoryStore = rest_stores["memories"]
        type_param = request.query_params.get("type")
        limit = int(request.query_params.get("limit", "100"))

        entity_type = EntityType(type_param) if type_param else None
        entities = await memories.list(entity_type=entity_type, limit=limit)

        return JSONResponse({"entities": [_serialize_entity(e) for e in entities]})

    @mcp.custom_route("/api/entities/{id}", methods=["GET"])
    async def api_get_entity(request: Request) -> JSONResponse:
        """Get a single entity by ID."""
        memories: MemoryStore = rest_stores["memories"]
        entity_id = request.path_params["id"]

        entity = await memories.get(UUID(entity_id))
        if not entity:
            return JSONResponse({"error": "Entity not found"}, status_code=404)

        return JSONResponse(_serialize_entity(entity))

    @mcp.custom_route("/api/entities", methods=["POST"])
    async def api_create_entity(request: Request) -> JSONResponse:
        """Create a new entity."""
        body = await request.json()
        memories: MemoryStore = rest_stores["memories"]

        entity = Entity(
            type=EntityType(body["type"]),
            content=body["content"],
            tags=body.get("tags"),
            pinned=body.get("pinned", False),
            created_session_id=UUID(body.get("session_id", str(uuid4()))),
        )
        created = await memories.create(entity)

        try:
            embedding = await encode_one(created.content)
            await memories.upsert_embedding(created.id, embedding)
        except Exception:
            pass

        return JSONResponse(_serialize_entity(created), status_code=201)

    @mcp.custom_route("/api/entities/{id}", methods=["PATCH"])
    async def api_update_entity(request: Request) -> JSONResponse:
        """Update an entity's content, tags, or pinned status."""
        memories: MemoryStore = rest_stores["memories"]
        entity_id = request.path_params["id"]
        body = await request.json()

        entity = await memories.get(UUID(entity_id))
        if not entity:
            return JSONResponse({"error": "Entity not found"}, status_code=404)

        if "content" in body:
            entity.content = body["content"]
        if "tags" in body:
            entity.tags = body["tags"]
        if "pinned" in body:
            entity.pinned = body["pinned"]

        entity.updated_at = datetime.now(timezone.utc)
        updated = await memories.update(entity)

        if "content" in body:
            try:
                embedding = await encode_one(updated.content)
                await memories.upsert_embedding(updated.id, embedding)
            except Exception:
                pass

        return JSONResponse(_serialize_entity(updated))

    @mcp.custom_route("/api/entities/{id}", methods=["DELETE"])
    async def api_delete_entity(request: Request) -> JSONResponse:
        """Soft-delete an entity."""
        memories: MemoryStore = rest_stores["memories"]
        entity_id = request.path_params["id"]

        entity = await memories.get(UUID(entity_id))
        if not entity:
            return JSONResponse({"error": "Entity not found"}, status_code=404)

        await memories.delete(UUID(entity_id))
        return JSONResponse({"deleted": True})

    @mcp.custom_route("/api/entities/{id}/pin", methods=["POST"])
    async def api_pin_entity(request: Request) -> JSONResponse:
        """Toggle pin status on an entity."""
        memories: MemoryStore = rest_stores["memories"]
        entity_id = request.path_params["id"]
        body = await request.json()

        entity = await memories.get(UUID(entity_id))
        if not entity:
            return JSONResponse({"error": "Entity not found"}, status_code=404)

        pinned = body.get("pinned", not entity.pinned)
        await memories.pin(UUID(entity_id), pinned)

        entity.pinned = pinned
        return JSONResponse(_serialize_entity(entity))

    @mcp.custom_route("/api/knowledge", methods=["GET"])
    async def api_list_knowledge(request: Request) -> JSONResponse:
        """List knowledge articles."""
        knowledge: KnowledgeStore = rest_stores["knowledge"]
        limit = int(request.query_params.get("limit", "50"))

        articles = await knowledge.list(limit=limit)

        return JSONResponse({"articles": [_serialize_knowledge(a) for a in articles]})

    @mcp.custom_route("/api/knowledge/{id}", methods=["GET"])
    async def api_get_knowledge(request: Request) -> JSONResponse:
        """Get a single knowledge article by ID."""
        knowledge: KnowledgeStore = rest_stores["knowledge"]
        article_id = request.path_params["id"]

        article = await knowledge.get(UUID(article_id))
        if not article:
            return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

        return JSONResponse(_serialize_knowledge(article))

    @mcp.custom_route("/api/knowledge", methods=["POST"])
    async def api_create_knowledge(request: Request) -> JSONResponse:
        """Create a new knowledge article."""
        body = await request.json()
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]

        article = Knowledge(
            topic=body["topic"],
            content=body["content"],
            tags=body.get("tags"),
            pinned=body.get("pinned", False),
            created_session_id=UUID(body.get("session_id", str(uuid4()))),
        )
        created = await knowledge_store.create(article)

        try:
            embedding = await encode_one(f"{created.topic} {created.content}")
            await knowledge_store.upsert_embedding(created.id, embedding)
        except Exception:
            pass

        return JSONResponse(_serialize_knowledge(created), status_code=201)

    @mcp.custom_route("/api/knowledge/{id}", methods=["PATCH"])
    async def api_update_knowledge(request: Request) -> JSONResponse:
        """Update a knowledge article's topic, content, tags, or pinned status."""
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]
        article_id = request.path_params["id"]
        body = await request.json()

        article = await knowledge_store.get(UUID(article_id))
        if not article:
            return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

        if "topic" in body:
            article.topic = body["topic"]
        if "content" in body:
            article.content = body["content"]
        if "tags" in body:
            article.tags = body["tags"]
        if "pinned" in body:
            article.pinned = body["pinned"]

        article.updated_at = datetime.now(timezone.utc)
        updated = await knowledge_store.upsert(article)

        if "topic" in body or "content" in body:
            try:
                embedding = await encode_one(f"{updated.topic} {updated.content}")
                await knowledge_store.upsert_embedding(updated.id, embedding)
            except Exception:
                pass

        return JSONResponse(_serialize_knowledge(updated))

    @mcp.custom_route("/api/knowledge/{id}", methods=["DELETE"])
    async def api_delete_knowledge(request: Request) -> JSONResponse:
        """Delete a knowledge article."""
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]
        article_id = request.path_params["id"]

        article = await knowledge_store.get(UUID(article_id))
        if not article:
            return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

        await knowledge_store.delete(UUID(article_id))
        return JSONResponse({"deleted": True})

    @mcp.custom_route("/api/knowledge/{id}/pin", methods=["POST"])
    async def api_pin_knowledge(request: Request) -> JSONResponse:
        """Toggle pin status on a knowledge article."""
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]
        article_id = request.path_params["id"]
        body = await request.json()

        article = await knowledge_store.get(UUID(article_id))
        if not article:
            return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

        pinned = body.get("pinned", not article.pinned)
        await knowledge_store.pin(UUID(article_id), pinned)

        article.pinned = pinned
        return JSONResponse(_serialize_knowledge(article))

    @mcp.custom_route("/api/sessions/list", methods=["GET"])
    async def api_list_sessions(request: Request) -> JSONResponse:
        """List recent sessions."""
        sessions: SessionStore = rest_stores["sessions"]
        limit = int(request.query_params.get("limit", "50"))

        session_list = await sessions.recent(limit=limit)

        return JSONResponse({"sessions": [_serialize_session(s) for s in session_list]})

    @mcp.custom_route("/api/sessions/{id}", methods=["GET"])
    async def api_get_session(request: Request) -> JSONResponse:
        """Get a single session by ID."""
        sessions: SessionStore = rest_stores["sessions"]
        session_id = request.path_params["id"]

        session = await sessions.get(UUID(session_id))
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)

        return JSONResponse(_serialize_session(session))

    @mcp.custom_route("/api/search", methods=["POST"])
    async def api_search(request: Request) -> JSONResponse:
        """Unified search — FTS5 with prefix matching, vector fallback."""
        body = await request.json()
        query = body.get("query", "")
        limit = body.get("limit", 10)

        if not query:
            return JSONResponse({"entities": [], "knowledge": []})

        memories: MemoryStore = rest_stores["memories"]
        knowledge: KnowledgeStore = rest_stores["knowledge"]

        fts_query = sanitize_fts_query(query)
        entity_results = []
        knowledge_results = []

        try:
            entity_results = await memories.search(fts_query, limit=limit)
        except Exception:
            pass

        try:
            knowledge_results = await knowledge.search(fts_query, limit=limit)
        except Exception:
            pass

        if not entity_results and not knowledge_results:
            try:
                embedding = await encode_one(query)
                entity_results = await memories.search_by_vector(embedding, limit=limit)
                knowledge_results = await knowledge.search_by_vector(embedding, limit=limit)
            except Exception:
                pass

        return JSONResponse({
            "entities": [_serialize_entity(e) for e in entity_results],
            "knowledge": [_serialize_knowledge(a) for a in knowledge_results],
        })

    @mcp.custom_route("/api/stats", methods=["GET"])
    async def api_stats(request: Request) -> JSONResponse:
        """Dashboard stats — entity counts by type, session count, knowledge count."""
        db = rest_stores["db"]

        cursor = await db.execute(
            "SELECT type, COUNT(*) as count FROM entities WHERE deleted_at IS NULL GROUP BY type"
        )
        entity_rows = await cursor.fetchall()
        entity_counts = {row["type"]: row["count"] for row in entity_rows}

        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM sessions WHERE deleted_at IS NULL AND what_happened IS NOT NULL"
        )
        session_row = await cursor.fetchone()
        session_count = session_row["count"] if session_row else 0

        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM knowledge WHERE deleted_at IS NULL"
        )
        knowledge_row = await cursor.fetchone()
        knowledge_count = knowledge_row["count"] if knowledge_row else 0

        return JSONResponse({
            "entities": entity_counts,
            "sessions": session_count,
            "knowledge": knowledge_count,
        })
