"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import os
import logging
import time

from typing import Literal, TypeAlias

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from charlieverse.config import config
from charlieverse.db import database
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, StoryStore

from charlieverse.mcp import tools_memory, tools_knowledge, tools_sessions, tools_stories
from charlieverse.mcp.context import StoreContext
from charlieverse.api import hooks, entities, stories, spa

logger = logging.getLogger(__name__)

@lifespan
async def app_lifespan(server):
    """Initialize database and stores on server start."""
    os.environ["HF_HUB_VERBOSITY"] = "error"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error" # Only show errors
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

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
        "stories": StoryStore(db),
    }

    # Rebuild FTS indexes on startup (fast, ensures consistency)
    try:
        await store_dict["memories"].rebuild_fts()
        await store_dict["knowledge"].rebuild_fts()
        await store_dict["stories"].rebuild_fts()
    except Exception:
        logger.exception("FTS rebuild failed on startup — search may be stale")

    # Rebuild vector indexes in the background (slow, don't block startup)
    try:
        await store_dict["memories"].rebuild_vec()
        await store_dict["knowledge"].rebuild_vec()
        await store_dict["stories"].rebuild_vec()
    except Exception:
        logger.exception("Vector rebuild failed — semantic search may be stale")

    try:
        yield store_dict
    finally:
        await db.close()


mcp = FastMCP("Charlieverse", lifespan=app_lifespan)
McpTransport: TypeAlias = Literal["stdio", "http", "sse", "streamable-http"]


# Store references for REST routes (populated during lifespan).
# Typed as dict so the api/ register_routes helpers (which accept dict) stay compatible.
_rest_stores: dict = {}

# session_id -> (IDs delivered at activation, timestamp).
# Entries older than 24h are evicted on access to prevent unbounded growth (C-02).
_SEEN_IDS_TTL = 86400  # 24 hours
_activation_seen_ids: dict[str, tuple[set[str], float]] = {}


def get_seen_ids(session_id: str) -> set[str]:
    """Get the set of activation IDs for a session, with TTL eviction."""
    _evict_stale_seen_ids()
    entry = _activation_seen_ids.get(session_id)
    return entry[0] if entry else set()


def set_seen_ids(session_id: str, ids: set[str]) -> None:
    """Store activation IDs for a session."""
    _activation_seen_ids[session_id] = (ids, time.monotonic())


def _evict_stale_seen_ids() -> None:
    """Remove entries older than TTL."""
    now = time.monotonic()
    stale = [k for k, (_, ts) in _activation_seen_ids.items() if now - ts > _SEEN_IDS_TTL]
    for k in stale:
        del _activation_seen_ids[k]


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

hooks.register_routes(mcp, _rest_stores)
entities.register_routes(mcp, _rest_stores)
stories.register_routes(mcp, _rest_stores)
spa.register_routes(mcp)
