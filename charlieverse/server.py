"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from aiosqlite import Connection
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from rich.console import Console

from charlieverse.api import entities, hooks, spa
from charlieverse.api import stories as stories_api
from charlieverse.config import config
from charlieverse.db import database
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.entities.mcp import server as memories
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.knowledge.mcp import server as knowledge
from charlieverse.memory.messages.mcp import server as messages
from charlieverse.memory.messages.store import MessageStore
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.sessions.mcp import server as sessions
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores, _StoreContext
from charlieverse.memory.stories import StoryStore
from charlieverse.memory.stories.mcp import server as stories
from charlieverse.types.id import ModelId

console = Console()


async def connect_to_db() -> Connection:
    console.log("Connecting to Database")
    db_path: Path = config.database
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return await database.connect(db_path)


async def setup_stores(db: Connection) -> _StoreContext:
    context: _StoreContext = {
        "memories": EntityStore(db),
        "sessions": SessionStore(db),
        "knowledge": KnowledgeStore(db),
        "stories": StoryStore(db),
        "messages": MessageStore(db),
    }

    async def rebuild(stores: _StoreContext) -> None:
        """Rebuild FTS + vector indexes for all tables."""
        from asyncio import gather

        console.log("Performing Database Maintenance")
        await stores["stories"].dedupe()

        await gather(
            stores["memories"].rebuild(),
            stores["knowledge"].rebuild(),
            stores["stories"].rebuild(),
            stores["messages"].rebuild(),
        )

    try:
        await rebuild(context)
    except Exception as e:
        console.log(f"Store Cleanup Failed {e}")

    return context


async def prewarm():
    # os.environ["HF_HUB_VERBOSITY"] = "error"
    # os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    # os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    console.log("Prewarming NLP and Embedding Models")
    from charlieverse.embeddings.service import prewarm_embeddings
    from charlieverse.nlp.extractor import prewarm_nlp

    try:
        await asyncio.gather(asyncio.to_thread(prewarm_embeddings), asyncio.to_thread(prewarm_nlp))
    except Exception as e:
        console.log(f"Prewarm Error: {e}")


async def start_server(host: str, port: int):
    await prewarm()
    db = await connect_to_db()
    store_context = await setup_stores(db)
    stores = Stores.from_context(store_context)

    @lifespan
    async def app_lifespan(server: FastMCP):
        """Initialize database and stores on server start."""
        yield store_context
        await db.close()

    mcp = FastMCP("Charlieverse", lifespan=app_lifespan)

    mcp.mount(sessions, namespace="session")
    mcp.mount(stories, namespace="story")
    mcp.mount(knowledge, namespace="knowledge")
    mcp.mount(knowledge, namespace="knowledge")
    mcp.mount(messages, namespace="messages")
    mcp.mount(memories)

    hooks.register_routes(mcp, stores)
    entities.register_routes(mcp, stores)
    stories_api.register_routes(mcp, stores)
    spa.register_routes(mcp)

    await mcp.run_async("http", host=host, port=port, show_banner=False)


# Store references for REST routes (populated during lifespan).
# Typed as dict so the api/ register_routes helpers (which accept dict) stay compatible.
_rest_stores: dict = {}

# session_id -> (IDs delivered at activation, timestamp).
# Entries older than 24h are evicted on access to prevent unbounded growth (C-02).
_SEEN_IDS_TTL = 86400  # 24 hours
_activation_seen_ids: dict[ModelId, tuple[set[ModelId], float]] = {}


def get_seen_ids(session_id: SessionId) -> set[ModelId]:
    """Get the set of activation IDs for a session, with TTL eviction."""
    _evict_stale_seen_ids()
    entry = _activation_seen_ids.get(session_id)
    return entry[0] if entry else set()


def set_seen_ids(session_id: SessionId, ids: set[ModelId]) -> None:
    """Store activation IDs for a session."""
    _activation_seen_ids[session_id] = (ids, time.monotonic())


def _evict_stale_seen_ids() -> None:
    """Remove entries older than TTL."""
    now = time.monotonic()
    stale = [k for k, (_, ts) in _activation_seen_ids.items() if now - ts > _SEEN_IDS_TTL]
    for k in stale:
        del _activation_seen_ids[k]


if __name__ == "__main__":
    asyncio.run(start_server(host=config.server.host, port=config.server.port))
