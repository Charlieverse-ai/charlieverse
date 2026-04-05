"""Store context — typed lifespan container passed to every MCP tool."""

from __future__ import annotations

from typing import TypedDict

from aiosqlite import Connection

from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.messages.store import MessageStore
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stories import StoryStore


class StoreContext(TypedDict):
    """Typed lifespan context passed to every MCP tool via ctx.lifespan_context."""

    db: Connection
    memories: EntityStore
    knowledge: KnowledgeStore
    sessions: SessionStore
    stories: StoryStore
    messages: MessageStore


async def rebuild_all(stores: StoreContext) -> None:
    """Rebuild FTS + vector indexes for all tables."""
    from asyncio import gather

    await stores["stories"].dedupe()

    await gather(
        stores["memories"].rebuild(),
        stores["knowledge"].rebuild(),
        stores["stories"].rebuild(),
        stores["messages"].rebuild(),
    )
