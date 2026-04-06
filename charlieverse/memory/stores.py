from __future__ import annotations

from typing import Any, Self, TypedDict

from attr import dataclass

from .entities.store import EntityStore
from .knowledge.store import KnowledgeStore
from .messages.store import MessageStore
from .sessions.store import SessionStore
from .stories.store import StoryStore


class StoreContext(TypedDict):
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
    def from_context(cls, context: dict[str, Any] | StoreContext) -> Self:
        stores = cls(
            memories=context["memories"],
            knowledge=context["knowledge"],
            sessions=context["sessions"],
            stories=context["stories"],
            messages=context["messages"],
        )
        return stores
