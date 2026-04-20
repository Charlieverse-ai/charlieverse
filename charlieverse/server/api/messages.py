from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.db.fts import clean_text
from charlieverse.memory.messages import MessageId, MessageRole, MessageStore
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import EmptyResponse, ExceptionResponse, MissingRequired, ModelListResponse, ModelResponse, SavedResponse
from charlieverse.types.dates import utc_now
from charlieverse.types.strings import NonEmptyString


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
            content = NonEmptyString(body.get("content"))

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
            if not clean_text(content):
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
    async def api_latest_message(request: Request) -> ModelResponse | EmptyResponse | ExceptionResponse:
        """Get the most recent message for a session, optionally filtered by role."""
        try:
            messages: MessageStore = rest_stores.messages
            session_id = SessionId.or_none(request.query_params.get("session_id"))
            if not session_id:
                return EmptyResponse()

            role_raw = request.query_params.get("role")
            role_param: MessageRole | None = MessageRole(role_raw) if role_raw else None

            session = await rest_stores.sessions.get(session_id)
            if not session:
                return EmptyResponse()

            message = await messages.latest(session, role=role_param)
            return ModelResponse(message) if message else EmptyResponse()
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/messages/search", methods=["POST"])
    async def api_search_messages(request: Request) -> ModelListResponse:
        """Search messages via FTS."""
        body = await request.json()
        messages: MessageStore = rest_stores.messages
        query = NonEmptyString(body.get("query"))
        limit = body.get("limit", 20)
        session_id = SessionId.or_none(body.get("session_id"))

        results = await messages.search(
            query,
            limit=limit,
            session_id=session_id,
        )

        return ModelListResponse(results)
