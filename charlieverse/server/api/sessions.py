"""REST endpoints for entity, knowledge, and session CRUD (web UI)."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.sessions import SessionId
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import (
    ExceptionResponse,
    ModelListResponse,
    ModelResponse,
    NotFoundResponse,
)


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
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
