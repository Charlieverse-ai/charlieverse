"""MCP tools: search_knowledge, update_knowledge."""

from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.mcp.context import _permalink, _stores
from charlieverse.tools import knowledge as knowledge_tools
from charlieverse.tools.responses import ExpertResponse


def register(mcp: FastMCP) -> None:
    """Register all knowledge MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def search_knowledge(
        query: str,
        limit: int = 5,
        ctx: Context = CurrentContext(),
    ) -> ExpertResponse:
        """Search the knowledge base. Semantic + full-text search across knowledge articles."""
        if not query.strip():
            raise ToolError("query cannot be empty")
        return await knowledge_tools.search_knowledge(
            query=query, limit=limit,
            knowledge_store=_stores(ctx)["knowledge"],
        )

    @mcp.tool
    async def update_knowledge(
        topic: str,
        content: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Create or update a knowledge article."""
        if not topic.strip():
            raise ToolError("topic cannot be empty")
        if not content.strip():
            raise ToolError("content cannot be empty")
        result = await knowledge_tools.update_knowledge(
            topic=topic, content=content, session_id=session_id,
            tags=tags, pinned=pinned,
            knowledge_store=_stores(ctx)["knowledge"],
        )
        return {"id": str(result.id), "url": _permalink("knowledge", str(result.id))}
