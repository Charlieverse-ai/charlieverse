"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from charlieverse.api import entities, hooks, spa, stories
from charlieverse.config import config
from charlieverse.db import database
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, StoryStore
from charlieverse.db.stores.context import StoreContext, rebuild_all
from charlieverse.mcp import (
    tools_knowledge,
    tools_memory,
    tools_sessions,
    tools_stories,
)

logger = logging.getLogger(__name__)

async def setup_stores() -> StoreContext:
    db_path = config.database
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await database.connect(db_path)

    context: StoreContext = {
        "db": db,
        "memories": MemoryStore(db),
        "sessions": SessionStore(db),
        "knowledge": KnowledgeStore(db),
        "stories": StoryStore(db),
    }

    try:
        await rebuild_all(context)
    except Exception as e:
        logger.exception(f"Store Cleanup Failed {e}")

    return context

async def prewarm():
    os.environ["HF_HUB_VERBOSITY"] = "error"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error" # Only show errors
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    from charlieverse.embeddings.service import prewarm_embeddings
    from charlieverse.nlp.extractor import prewarm_nlp

    try:
        await asyncio.gather(
            asyncio.to_thread(prewarm_embeddings),
            asyncio.to_thread(prewarm_nlp)
        )
    except Exception as e:
        logger.exception(f"Prewarm Error: {e}")

async def start_server(host: str, port: int):
    await prewarm()
    stores = await setup_stores()

    @lifespan
    async def app_lifespan(server: FastMCP):
        """Initialize database and stores on server start."""
        yield stores
        await stores["db"].close()

    mcp = FastMCP("Charlieverse", lifespan=app_lifespan)

    # MCP tools
    tools_memory.register(mcp)
    tools_knowledge.register(mcp)
    tools_sessions.register(mcp)
    tools_stories.register(mcp)

    # Custom Routes
    hooks.register_routes(mcp, stores)
    entities.register_routes(mcp, stores)
    stories.register_routes(mcp, stores)
    spa.register_routes(mcp)

    await mcp.run_async("http", host=host, port=port, show_banner=False)

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


# # Patch lifespan to also populate REST store refs
# _original_lifespan = app_lifespan


# @lifespan
# async def _patched_lifespan(server):
#     async with _original_lifespan(server) as stores:
#         _rest_stores.update(stores)
#         yield stores


# # Re-create mcp with patched lifespan
# mcp._lifespan = _patched_lifespan

