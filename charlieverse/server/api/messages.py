from __future__ import annotations

from uuid import uuid4

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.memory.messages import MessageId, MessageRole, MessageStore
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import ModelListResponse
from charlieverse.types.dates import utc_now


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/messages", methods=["POST"])
    async def api_save_message(request: Request) -> JSONResponse:
        """Save a message captured from hooks."""
        body = await request.json()
        messages: MessageStore = rest_stores.messages

        msg_id = body.get("id", str(uuid4()))
        session_id = body.get("session_id")
        role = body.get("role")
        content = str(body.get("content", "")).strip()

        if not session_id or not role or not content:
            return JSONResponse({"error": "Missing Required params"}, status_code=400)

        # TODO: Move this into a validation helper
        if "<task-notification>" in content and "</task-notification>" in content:
            return JSONResponse({"saved": False, "reason": "Not saved because the user message is not valid"})

        await messages.save(
            msg_id=MessageId(msg_id),
            session_id=SessionId(session_id),
            role=MessageRole(role),
            content=content,
            created_at=utc_now().isoformat(),
        )
        return JSONResponse({"saved": True})

    @mcp.custom_route("/api/messages/latest", methods=["GET"])
    async def api_latest_message(request: Request) -> JSONResponse:
        """Get the most recent message for a session, optionally filtered by role."""
        messages: MessageStore = rest_stores.messages
        session_id_param = request.query_params.get("session_id")
        role_param = request.query_params.get("role")

        msg = await messages.latest(
            session_id=SessionId(session_id_param) if session_id_param else None,
            role=role_param,
        )
        if not msg:
            return JSONResponse({})

        return JSONResponse(
            {
                "id": msg.id,
                "session_id": msg.session_id,
                "role": msg.role.value,
                "content": msg.content[:200],
                "created_at": msg.created_at.isoformat(),
            }
        )

    @mcp.custom_route("/api/messages/search", methods=["POST"])
    async def api_search_messages(request: Request) -> ModelListResponse:
        """Search messages via FTS."""
        body = await request.json()
        messages: MessageStore = rest_stores.messages
        query = body.get("query", "")
        limit = body.get("limit", 20)
        session_id = body.get("session_id")

        results = await messages.search(
            query,
            limit=limit,
            session_id=SessionId(session_id) if session_id else None,
        )

        return ModelListResponse(results)
