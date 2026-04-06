from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.mcp.context import _stores
from charlieverse.memory.sessions import SessionId
from charlieverse.types.strings import ShortString


def register(mcp: FastMCP) -> None:
    """Register all message MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def search_messages(
        query: ShortString,
        limit: int = 20,
        session_id: SessionId | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Search past messages in conversations. Returns matching messages with role and date."""
        if not query.strip():
            raise ToolError("query cannot be empty")
        messages = _stores(ctx).messages
        results = await messages.search(query, limit=limit, session_id=session_id)
        return {
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role.value,
                    "content": m.content[:500],
                    "created_at": m.created_at.isoformat(),
                }
                for m in results
            ]
        }
