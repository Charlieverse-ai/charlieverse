from typing import TypedDict

import aiosqlite

from charlieverse.db.stores.memory_store import MemoryStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stories import StoryStore


class StoreContext(TypedDict):
    """Typed lifespan context passed to every MCP tool via ctx.lifespan_context."""

    db: aiosqlite.Connection
    memories: MemoryStore
    knowledge: KnowledgeStore
    sessions: SessionStore
    stories: StoryStore


async def rebuild_all(stores: StoreContext):
    """Rebuild FTS + vector indexes for all tables."""
    from asyncio import gather

    await stores["stories"].dedupe()

    await gather(
        stores["memories"].rebuild(),
        stores["knowledge"].rebuild(),
        stores["stories"].rebuild(),
    )
