"""Response from the recall tool — entities + knowledge + stories combined."""

from __future__ import annotations

from pydantic import BaseModel

from charlieverse.memory.entities import EntityId
from charlieverse.memory.knowledge import KnowledgeId
from charlieverse.memory.messages import MessageId
from charlieverse.memory.stories import StoryId


class KnowledgeSummary(BaseModel):
    """Compact knowledge representation for become_expert and recall results."""

    id: KnowledgeId
    content: str
    truncated: bool = False


class MessageSummary(BaseModel):
    """A message search result."""

    id: MessageId
    role: str
    content: str
    age: str = ""


class EntitySummary(BaseModel):
    """Compact entity representation for recall and list results."""

    id: EntityId
    type: str
    content: str
    age: str
    truncated: bool = False


class StorySummary(BaseModel):
    """A story search result — truncated content for recall."""

    id: StoryId
    title: str
    tier: str
    summary: str | None = None
    truncated: bool = False
