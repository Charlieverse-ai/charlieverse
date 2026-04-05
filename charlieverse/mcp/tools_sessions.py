"""MCP tools: search_messages, session_update."""

from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import CurrentContext

from charlieverse.mcp.context import _stores
from charlieverse.memory.sessions import SessionContent, SessionId
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString

from .responses import PermalinkResponse


def register(mcp: FastMCP) -> None:
    """Register all session MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def session_update(
        session_id: SessionId,
        workspace: NonEmptyString,
        content: SessionContent | None = None,
        tags: TagList | None = None,
        ctx: Context = CurrentContext(),
    ) -> PermalinkResponse:
        """Update the session with the provided fields. Omit a field to keep the existing value"""
        from charlieverse.memory.sessions import UpdateSession

        session_store = _stores(ctx)["sessions"]

        session = UpdateSession(
            id=session_id,
            content=content,
            tags=tags,
            workspace=workspace,
        )

        await session_store.upsert(session)
        return PermalinkResponse("sessions", session_id)
