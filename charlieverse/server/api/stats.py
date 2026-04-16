"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.stores import Stores
from charlieverse.server.responses import (
    ExceptionResponse,
    ModelResponse,
    Stats,
)


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/stats", methods=["GET"])
    async def api_stats(request: Request) -> ModelResponse | ExceptionResponse:
        """Dashboard stats — entity counts by type, session count, knowledge count."""
        try:
            return ModelResponse(
                Stats(
                    entities=await rest_stores.memories.count_by_type(),
                    sessions=await rest_stores.sessions.count_with_summary(),
                    knowledge=await rest_stores.knowledge.count(),
                )
            )
        except Exception as e:
            return ExceptionResponse(e)
