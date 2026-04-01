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


async def _dedup_stories(store: StoryStore) -> None:
    """Remove duplicate rollup stories, keeping the most recently updated."""
    cursor = await store.db.execute("""
        SELECT tier, period_start, period_end, COUNT(*) as cnt
        FROM stories
        WHERE deleted_at IS NULL AND session_id IS NULL
        GROUP BY tier, SUBSTR(period_start, 1, 10), SUBSTR(period_end, 1, 10)
        HAVING cnt > 1
    """)
    groups = list(await cursor.fetchall())
    if not groups:
        return

    deleted = 0
    for row in groups:
        tier, p_start, p_end = row[0], row[1], row[2]
        dupes = await store.db.execute(
            """SELECT id FROM stories
               WHERE tier = ? AND SUBSTR(period_start, 1, 10) = SUBSTR(?, 1, 10) AND SUBSTR(period_end, 1, 10) = SUBSTR(?, 1, 10)
               AND deleted_at IS NULL AND session_id IS NULL
               ORDER BY updated_at DESC""",
            (tier, p_start, p_end),
        )
        ids = [r[0] for r in await dupes.fetchall()]
        # Keep the first (most recently updated), soft-delete the rest
        for stale_id in ids[1:]:
            from uuid import UUID
            await store.delete(UUID(stale_id))
            deleted += 1

    if deleted:
        logger.info("Deduped %d rollup stories across %d groups", deleted, len(groups))


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

    # Deduplicate rollup stories (same tier + period window)
    try:
        await _dedup_stories(store_dict["stories"])
    except Exception:
        logger.exception("Story dedup failed on startup")

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
