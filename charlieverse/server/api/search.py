"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.db.fts import clean_text
from charlieverse.embeddings import encode_one
from charlieverse.memory.entities import (
    EntityStore,
)
from charlieverse.memory.knowledge import (
    KnowledgeStore,
)
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import (
    ExceptionResponse,
    ModelResponse,
    SearchResults,
)


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
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
