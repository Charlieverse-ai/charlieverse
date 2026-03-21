"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import asyncio
from typing import Literal, TypeAlias

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from charlieverse.config import config
from charlieverse.db import database
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, StoryStore, WorkLogStore

from charlieverse.mcp import tools_memory, tools_knowledge, tools_sessions, tools_stories
from charlieverse.mcp.context import StoreContext
from charlieverse.api import hooks, entities, stories, spa


@lifespan
async def app_lifespan(server):
    """Initialize database and stores on server start."""
    db_path = config.database
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = await database.connect(db_path)

    # Pre-warm models so first requests aren't slow
    from charlieverse.embeddings.service import _get_model
    _get_model()

    from charlieverse.nlp.extractor import _get_nlp
    _get_nlp()

    store_dict: StoreContext = {
        "db": db,
        "memories": MemoryStore(db),
        "sessions": SessionStore(db),
        "knowledge": KnowledgeStore(db),
        "work_logs": WorkLogStore(db),
        "stories": StoryStore(db),
    }

    # Rebuild FTS indexes on startup (fast, ensures consistency)
    try:
        await store_dict["memories"].rebuild_fts()
        await store_dict["knowledge"].rebuild_fts()
        await store_dict["stories"].rebuild_fts()
    except Exception:
        pass

    # Rebuild vector indexes in the background (slow, don't block startup)
    async def _background_vec_rebuild():
        try:
            await store_dict["memories"].rebuild_vec()
            await store_dict["knowledge"].rebuild_vec()
            await store_dict["stories"].rebuild_vec()
        except Exception:
            pass

    rebuild_task = asyncio.create_task(_background_vec_rebuild())

    try:
        yield store_dict
    finally:
        rebuild_task.cancel()
        await db.close()


mcp = FastMCP("Charlieverse", lifespan=app_lifespan)
McpTransport: TypeAlias = Literal["stdio", "http", "sse", "streamable-http"]


# Store references for REST routes (populated during lifespan).
# Typed as dict so the api/ register_routes helpers (which accept dict) stay compatible.
_rest_stores: dict = {}
_activation_seen_ids: dict[str, set[str]] = {}  # session_id -> IDs delivered at activation


# Patch lifespan to also populate REST store refs
_original_lifespan = app_lifespan


@lifespan
async def _patched_lifespan(server):
    async with _original_lifespan(server) as stores:
        _rest_stores.update(stores)
        yield stores


# Re-create mcp with patched lifespan
mcp._lifespan = _patched_lifespan


# ============================================================
# Register MCP tools
# ============================================================

tools_memory.register(mcp)
tools_knowledge.register(mcp)
tools_sessions.register(mcp)
tools_stories.register(mcp)


# ============================================================
# Register REST routes
# ============================================================

hooks.register_routes(mcp, _rest_stores, _activation_seen_ids)
entities.register_routes(mcp, _rest_stores)
stories.register_routes(mcp, _rest_stores)
spa.register_routes(mcp)
