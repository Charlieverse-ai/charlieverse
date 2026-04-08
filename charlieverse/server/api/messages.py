from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.messages import MessageId, MessageRole, MessageStore
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import EmptyResponse, ExceptionResponse, MissingRequired, ModelListResponse, ModelResponse, SavedResponse
from charlieverse.types.dates import utc_now


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/messages", methods=["POST"])
    async def api_save_message(request: Request) -> SavedResponse | EmptyResponse | MissingRequired | ExceptionResponse:
        """Save a message captured from hooks."""
        try:
            body = await request.json()
            messages: MessageStore = rest_stores.messages

            msg_id = MessageId(body.get("id", MessageId()))
            session_id = SessionId(body.get("session_id"))
            role = MessageRole(body.get("role"))
            content = str(body.get("content", "")).strip()

            if not session_id or not role or not content:
                missing: list[str] = []
                if not session_id:
                    missing.append("session_id")
                if not role:
                    missing.append("role")
                if not content:
                    missing.append("content")

                return MissingRequired(",".join(missing))

            # TODO: Move this into a validation helper
            if "<task-notification>" in content and "</task-notification>" in content:
                return EmptyResponse()

            await messages.save(
                msg_id=msg_id,
                session_id=session_id,
                role=role,
                content=content,
                created_at=utc_now().isoformat(),
            )
            return SavedResponse()
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/messages/latest", methods=["GET"])
    async def api_latest_message(request: Request) -> ModelResponse | EmptyResponse:
        """Get the most recent message for a session, optionally filtered by role."""
        messages: MessageStore = rest_stores.messages
        session_id_param = request.query_params.get("session_id")
        role_param = request.query_params.get("role")

        message = await messages.latest(
            session_id=SessionId(session_id_param) if session_id_param else None,
            role=role_param,
        )

        return ModelResponse(message) if message else EmptyResponse()

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
