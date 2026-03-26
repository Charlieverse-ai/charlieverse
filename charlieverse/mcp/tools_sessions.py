"""MCP tools: search_messages, session_update."""

from __future__ import annotations

from uuid import uuid4

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.db.stores import SessionStore
from charlieverse.mcp.context import _permalink, _stores


def register(mcp: FastMCP) -> None:
    """Register all session MCP tools on the given FastMCP instance."""

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
        return {
            "messages": [
                {"id": row["id"], "role": row["role"],
                 "content": row["content"][:500], "created_at": row["created_at"]}
                for row in rows
            ]
        }

    @mcp.tool
    async def session_update(
        what_happened: str,
        for_next_session: str,
        tags: list[str],
        session_id: str | None = None,
        workspace: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Save a detailed snapshot of the current session — what happened and what's next."""
        if not what_happened.strip():
            raise ToolError("what_happened cannot be empty")
        if not for_next_session.strip():
            raise ToolError("for_next_session cannot be empty")

        from charlieverse.tools.sessions import session_update as _session_update

        stores = _stores(ctx)
        sessions: SessionStore = stores["sessions"]

        sid = session_id or str(uuid4())

        result = await _session_update(
            id=sid,
            what_happened=what_happened,
            for_next_session=for_next_session,
            tags=tags,
            workspace=workspace,
            sessions=sessions,
        )
        return {"saved": True, "session_id": sid, "url": _permalink("sessions", sid)}
