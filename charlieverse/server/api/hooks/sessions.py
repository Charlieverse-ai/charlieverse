from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from charlieverse.context import ActivationBuilder
from charlieverse.context import renderer as context_renderer
from charlieverse.memory.sessions import Session, SessionId, UpdateSession
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register hook REST endpoints on the given FastMCP instance."""
    # Lazy import to avoid circular dependency (hooks → server → mcp → tools → server)
    from charlieverse.server.utils.seen_models import set_seen_ids

    @mcp.custom_route("/api/sessions/context", methods=["GET"])
    async def api_session_context(request: Request) -> PlainTextResponse:
        """Preview activation context for debugging. Returns rendered context as plain text."""
        sessions_store: SessionStore = rest_stores.sessions

        session_id = request.query_params.get("session_id")
        workspace = request.query_params.get("workspace")
        session: Session | None = None

        if not session_id:
            recent_sessions = await sessions_store.recent(limit=1, workspace=workspace)
            session = recent_sessions[0] if recent_sessions else None
        else:
            session = await sessions_store.get(SessionId(session_id))

        if not session:
            return PlainTextResponse("Missing")

        builder = ActivationBuilder(rest_stores)
        bundle = await builder.build(session, workspace)
        activation = context_renderer.render(bundle)

        return PlainTextResponse(activation)

    @mcp.custom_route("/api/sessions/start", methods=["POST"])
    async def api_session_start(request: Request) -> JSONResponse:
        """Start or resume a session. Returns activation."""
        body = await request.json()
        session_id = body.get("session_id", SessionId())
        workspace = body.get("workspace")

        sessions_store: SessionStore = rest_stores.sessions

        session = await sessions_store.upsert(UpdateSession(id=session_id, workspace=workspace))

        builder = ActivationBuilder(rest_stores)
        bundle = await builder.build(session, workspace)
        activation = context_renderer.render(bundle)

        set_seen_ids(session.id, bundle.seen_ids)

        return JSONResponse(
            {
                "session_id": session.id,
                "activation": activation,
            }
        )

    @mcp.custom_route("/api/sessions/end", methods=["POST"])
    async def api_session_end(request: Request) -> JSONResponse:
        """End a session."""
        return JSONResponse({"status": "ok"})
