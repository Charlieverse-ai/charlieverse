from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.messages import MessageRole
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import ExceptionResponse, ModelResponse, NotFoundResponse
from charlieverse.server.responses.prompt_submit_delta import PromptSubmitContext


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/session/{session_id}/prompt_submit", methods=["GET"])
    async def prompt_submit(request: Request) -> NotFoundResponse | ExceptionResponse | ModelResponse:
        try:
            session_id = SessionId(request.path_params.get("session_id"))
            session = await rest_stores.sessions.get(session_id)

            if not session:
                return NotFoundResponse("Session")

            user_message = await rest_stores.messages.latest(session=session, role=MessageRole.user)
            assistant_message = await rest_stores.messages.latest(session=session, role=MessageRole.charlie)

            return ModelResponse(
                PromptSubmitContext.from_session(
                    session=session,
                    user_message=user_message,
                    assistant_message=assistant_message,
                )
            )
        except Exception as e:
            return ExceptionResponse(e)
