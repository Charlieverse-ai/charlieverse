from __future__ import annotations

from typing import Self, TypedDict

from attr import dataclass
from fastmcp import Context

from .entities.store import EntityStore
from .knowledge.store import KnowledgeStore
from .messages.store import MessageStore
from .sessions.store import SessionStore
from .stories.store import StoryStore


class _StoreContext(TypedDict):
    """Typed lifespan context passed to every MCP tool via ctx.lifespan_context."""

    memories: EntityStore
    knowledge: KnowledgeStore
    sessions: SessionStore
    stories: StoryStore
    messages: MessageStore


@dataclass
class Stores:
    memories: EntityStore
    knowledge: KnowledgeStore
    sessions: SessionStore
    stories: StoryStore
    messages: MessageStore

    @classmethod
    def from_context(cls, context: Context | _StoreContext) -> Self:
        store_context = context.lifespan_context if isinstance(context, Context) else context

        stores = cls(
            memories=store_context["memories"],
            knowledge=store_context["knowledge"],
            sessions=store_context["sessions"],
            stories=store_context["stories"],
            messages=store_context["messages"],
        )
        return stores
