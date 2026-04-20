"""Response from the recall tool — entities + knowledge + stories combined."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from charlieverse.helpers.text import strip_markdown
from charlieverse.helpers.time_utils import relative_date
from charlieverse.memory.entities import Entity, EntityId
from charlieverse.memory.knowledge import KnowledgeId
from charlieverse.memory.messages import MessageId
from charlieverse.memory.stories import StoryId

MAX_ENTITY_CONTENT = 500
MAX_KNOWLEDGE_CONTENT = 500
MAX_STORY_CONTENT = 300
MAX_MESSAGE_CONTENT = 300


def truncate(text: str, max_len: int, *, plaintext: bool = True) -> tuple[str, bool]:
    """Truncate text to max_len, appending '…' if trimmed. Returns (text, was_truncated).

    If plaintext=True (default), strips markdown formatting first for denser content.
    """
    s = strip_markdown(text) if plaintext else text
    if len(s) <= max_len:
        return s, False
    return s[:max_len] + "…", True


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

    @classmethod
    def from_memory(cls, memory: Entity, should_truncate: bool = True) -> Self:
        if should_truncate:
            content, truncated = truncate(memory.content, MAX_ENTITY_CONTENT)
        else:
            content = memory.content
            truncated = False

        return cls.model_construct(
            id=memory.id,
            type=memory.type.value,
            content=content,
            age=relative_date(memory.created_at),
            truncated=truncated,
        )


class StorySummary(BaseModel):
    """A story search result — truncated content for recall."""

    id: StoryId
    title: str
    tier: str
    summary: str | None = None
    truncated: bool = False
