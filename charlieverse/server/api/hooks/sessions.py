from __future__ import annotations

import time

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from charlieverse.context import ActivationBuilder, ContextBundle
from charlieverse.context.renderer import ActivationContextRenderer
from charlieverse.memory.sessions import NewSession, Session, SessionId
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.types.strings import WorkspaceFilePath

# Bundle cache — keyed by session_id, expires after 60s.
# Multiple section hooks hit the server in quick succession for the same session;
# caching avoids rebuilding the bundle (and re-running embeddings) for each one.
_CACHE_TTL = 60.0
_bundle_cache: dict[str, tuple[ContextBundle, float]] = {}


async def _get_or_build_bundle(session_id: SessionId, workspace: WorkspaceFilePath | None, stores: Stores) -> ContextBundle:
    """Return a cached bundle or build a fresh one."""
    key = str(session_id)
    now = time.monotonic()
    cached = _bundle_cache.get(key)

    if cached:
        bundle, ts = cached
        if now - ts < _CACHE_TTL:
            return bundle
    builder = ActivationBuilder(stores)
    bundle = await builder.build(session_id, workspace)
    _bundle_cache[key] = (bundle, now)
    return bundle


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

        workspace = WorkspaceFilePath(workspace) if workspace else None

        if not session_id:
            recent_sessions = await sessions_store.recent(limit=1, workspace=workspace)
            session = recent_sessions[0] if recent_sessions else None
        else:
            session = await sessions_store.get(SessionId(session_id))

        if not session:
            return PlainTextResponse("Missing")

        bundle = await _get_or_build_bundle(session.id, workspace, rest_stores)
        activation = ActivationContextRenderer(bundle).render()

        return PlainTextResponse(activation)

    @mcp.custom_route("/api/sessions/start", methods=["POST"])
    async def api_session_start(request: Request) -> PlainTextResponse:
        """Start or resume a session. Returns activation (full or single section)."""
        body = await request.json()
        session_id = SessionId(body.get("session_id"))
        workspace = body.get("workspace")

        sessions_store: SessionStore = rest_stores.sessions

        await sessions_store.ensure(NewSession(id=session_id, workspace=workspace))

        bundle = await _get_or_build_bundle(session_id, workspace, rest_stores)
        activation = ActivationContextRenderer(bundle).render()

        set_seen_ids(session_id, bundle.seen_ids)

        return PlainTextResponse(activation)

    @mcp.custom_route("/api/sessions/end", methods=["POST"])
    async def api_session_end(request: Request) -> JSONResponse:
        """End a session."""
        return JSONResponse({"status": "ok"})
