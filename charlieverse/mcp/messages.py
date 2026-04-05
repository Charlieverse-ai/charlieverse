from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.mcp.context import _stores


def register(mcp: FastMCP) -> None:
    """Register all message MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def search_messages(
        query: str,
        limit: int = 20,
        session_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Search past messages in conversations. Returns matching messages with role and date."""
        if not query.strip():
            raise ToolError("query cannot be empty")
        db = _stores(ctx)["db"]
        safe_query = sanitize_fts_query(query)
        if not safe_query:
            return {"messages": []}
        if session_id:
            cursor = await db.execute(
                """SELECT m.* FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   WHERE messages_fts MATCH ? AND m.session_id = ?
                   ORDER BY bm25(messages_fts) LIMIT ?""",
                (safe_query, session_id, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT m.* FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   WHERE messages_fts MATCH ?
                   ORDER BY bm25(messages_fts) LIMIT ?""",
                (safe_query, limit),
            )

        rows = await cursor.fetchall()
        return {"messages": [{"id": row["id"], "role": row["role"], "content": row["content"][:500], "created_at": row["created_at"]} for row in rows]}
