"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiosqlite import Connection
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from rich.console import Console

from charlieverse.config import config
from charlieverse.db import database
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.entities.mcp import server as memories
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.knowledge.mcp import server as knowledge
from charlieverse.memory.messages.mcp import server as messages
from charlieverse.memory.messages.store import MessageStore
from charlieverse.memory.sessions.mcp import server as sessions
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores, _StoreContext
from charlieverse.memory.stories import StoryStore
from charlieverse.memory.stories.mcp import server as stories
from charlieverse.server.api import register_routes

console = Console()


async def _connect_to_db() -> Connection:
    console.log("Connecting to Database")
    db_path: Path = config.database
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return await database.connect(db_path)


async def _setup_stores(db: Connection) -> _StoreContext:
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


async def _prewarm():
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
    await _prewarm()
    db = await _connect_to_db()
    store_context = await _setup_stores(db)
    stores = Stores.from_context(store_context)

    @lifespan
    async def app_lifespan(server: FastMCP):
        """Initialize database and stores on server start."""
        yield store_context
        await db.close()

    mcp = FastMCP("Charlieverse", lifespan=app_lifespan)

    # Middleware
    mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=False, transform_errors=True))

    # Mount
    mcp.mount(sessions, namespace="session")
    mcp.mount(stories, namespace="story")
    mcp.mount(knowledge, namespace="knowledge")
    mcp.mount(knowledge, namespace="knowledge")
    mcp.mount(messages, namespace="messages")
    mcp.mount(memories)

    # Custom Routes
    register_routes(mcp, stores)

    await mcp.run_async("http", host=host, port=port, show_banner=False)


if __name__ == "__main__":
    asyncio.run(start_server(host=config.server.host, port=config.server.port))
