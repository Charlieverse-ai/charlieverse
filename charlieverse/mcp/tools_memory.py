"""MCP tools: remember_*, recall, update_memory, forget, pin."""

from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import CurrentContext

from charlieverse.mcp.context import _permalink, _remember_with_url, _stores
from charlieverse.tools import memory as memory_tools


def register(mcp: FastMCP) -> None:
    """Register all memory MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def remember_decision(
        decision: str,
        rationale: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a decision and why it was made."""
        result = await memory_tools.remember_decision(
            content=decision, rationale=rationale, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_solution(
        problem: str,
        solution: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a problem and how it was solved."""
        result = await memory_tools.remember_solution(
            problem=problem, solution=solution, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_preference(
        content: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a user preference or working style note."""
        result = await memory_tools.remember_preference(
            content=content, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_person(
        content: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a person — who they are, relationship, context."""
        result = await memory_tools.remember_person(
            content=content, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_milestone(
        milestone: str,
        significance: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a significant achievement or moment."""
        result = await memory_tools.remember_milestone(
            milestone=milestone, significance=significance, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_moment(
        moment: str,
        feeling: str | None = None,
        context: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ):
        """Remember a moment from our interactions — write it like a journal entry."""
        result = await memory_tools.remember_moment(
            moment=moment, feeling=feeling, context=context, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def recall(
        query: str,
        limit: int = 10,
        type: str | None = None,
        ctx: Context = CurrentContext(),
    ):
        """Search across entities and knowledge. Results are relevance-ordered."""
        return await memory_tools.recall(
            query=query, limit=limit, type=type,
            memories=_stores(ctx)["memories"],
            knowledge_store=_stores(ctx)["knowledge"],
            db=_stores(ctx)["db"],
        )

    @mcp.tool
    async def update_memory(
        id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
        ctx: Context = CurrentContext(),
    ):
        """Update an existing memory's content and/or tags. Preserves creation date and provenance."""
        await memory_tools.update_memory(
            id=id, content=content, tags=tags, session_id=session_id,
            memories=_stores(ctx)["memories"],
        )
        return {"id": id, "url": _permalink("memories", id)}

    @mcp.tool
    async def forget(
        id: str,
        ctx: Context = CurrentContext(),
    ):
        """Soft-delete an entity."""
        return await memory_tools.forget(id=id, memories=_stores(ctx)["memories"])

    @mcp.tool
    async def pin(
        id: str,
        pinned: bool,
        ctx: Context = CurrentContext(),
    ):
        """Pin or unpin an entity. Pinned entities appear in every session's context."""
        return await memory_tools.pin(id=id, pinned=pinned, memories=_stores(ctx)["memories"])
