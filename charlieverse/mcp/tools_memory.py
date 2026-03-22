"""MCP tools: remember_*, recall, update_memory, forget, pin."""

from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.mcp.context import _permalink, _remember_with_url, _stores
from charlieverse.tools import memory as memory_tools
from charlieverse.tools.responses import AckResponse, RecallResponse


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
    ) -> dict:
        """Remember a decision and why it was made."""
        if not decision.strip():
            raise ToolError("decision cannot be empty")
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
    ) -> dict:
        """Remember a problem and how it was solved."""
        if not problem.strip():
            raise ToolError("problem cannot be empty")
        if not solution.strip():
            raise ToolError("solution cannot be empty")
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
    ) -> dict:
        """Remember a user preference or working style note."""
        if not content.strip():
            raise ToolError("content cannot be empty")
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
    ) -> dict:
        """Remember a person — who they are, relationship, context."""
        if not content.strip():
            raise ToolError("content cannot be empty")
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
    ) -> dict:
        """Remember a significant achievement or moment."""
        if not milestone.strip():
            raise ToolError("milestone cannot be empty")
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
    ) -> dict:
        """Remember a moment from our interactions — write it like a journal entry."""
        if not moment.strip():
            raise ToolError("moment cannot be empty")
        result = await memory_tools.remember_moment(
            moment=moment, feeling=feeling, context=context, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_project(
        name: str,
        details: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Remember a project — name, details, what it is."""
        if not name.strip():
            raise ToolError("name cannot be empty")
        result = await memory_tools.remember_project(
            name=name, details=details, session_id=session_id,
            tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def remember_event(
        what: str,
        when: str,
        who: str | None = None,
        where: str | None = None,
        why: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        pinned: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Remember an event — something that happened or is happening."""
        if not what.strip():
            raise ToolError("what cannot be empty")
        if not when.strip():
            raise ToolError("when cannot be empty")
        result = await memory_tools.remember_event(
            what=what, when=when, who=who, where=where, why=why,
            session_id=session_id, tags=tags, pinned=pinned,
            memories=_stores(ctx)["memories"],
        )
        return await _remember_with_url(result)

    @mcp.tool
    async def recall(
        query: str,
        limit: int = 10,
        type: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> RecallResponse:
        """Search across entities and knowledge. Results are relevance-ordered."""
        if not query.strip():
            raise ToolError("query cannot be empty")
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
    ) -> dict:
        """Update an existing memory's content and/or tags. Preserves creation date and provenance."""
        if not id.strip():
            raise ToolError("id cannot be empty")
        await memory_tools.update_memory(
            id=id, content=content, tags=tags, session_id=session_id,
            memories=_stores(ctx)["memories"],
        )
        return {"url": _permalink("memories", id)}

    @mcp.tool
    async def forget(
        id: str,
        ctx: Context = CurrentContext(),
    ) -> AckResponse:
        """Soft-delete an entity."""
        if not id.strip():
            raise ToolError("id cannot be empty")
        return await memory_tools.forget(id=id, memories=_stores(ctx)["memories"])

    @mcp.tool
    async def pin(
        id: str,
        pinned: bool,
        ctx: Context = CurrentContext(),
    ) -> AckResponse:
        """Pin or unpin an entity. Pinned entities appear in every session's context."""
        if not id.strip():
            raise ToolError("id cannot be empty")
        return await memory_tools.pin(id=id, pinned=pinned, memories=_stores(ctx)["memories"])
