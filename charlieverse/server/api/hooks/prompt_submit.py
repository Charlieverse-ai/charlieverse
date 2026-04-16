from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.memory.messages import MessageRole
from charlieverse.memory.messages.models import LatestMessage
from charlieverse.memory.sessions import Session, SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import ExceptionResponse, NotFoundResponse
from charlieverse.server.utils.seen_models import get_seen_ids
from charlieverse.types.dates import utc_now


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/session/{session_id}/prompt_submit", methods=["GET"])
    async def prompt_submit(request: Request) -> NotFoundResponse | ExceptionResponse | _TimeSince:
        try:
            session_id = SessionId(request.path_params.get("session_id"))
            session = await rest_stores.sessions.get(session_id)

            if not session:
                return NotFoundResponse("Session")

            user_message = await rest_stores.messages.latest(session_id=session_id, role=MessageRole.user)

            return _TimeSince(
                session=session,
                user_message=user_message,
            )
        except Exception as e:
            return ExceptionResponse(e)


class _TimeSince(JSONResponse):
    def __init__(
        self,
        session: Session,
        user_message: LatestMessage | None,
    ):
        now = utc_now()
        session_start = (now - session.created_at).total_seconds()
        last_save = (now - session.updated_at).total_seconds() if session.created_at != session.updated_at else None
        last_user_message = (now - user_message.created_at).total_seconds() if user_message else None
        message_count = user_message.message_count if user_message else 0

        super().__init__(
            {
                "session_start": session_start,
                "last_save": last_save,
                "last_user_message": last_user_message,
                "seen_memory_ids": list(get_seen_ids(session.id)),
                "message_count": message_count,
            }
        )
