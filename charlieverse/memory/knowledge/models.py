"""Knowledge model — persistent expertise articles that grow over time."""

from __future__ import annotations

from typing import Self

import aiosqlite
from pydantic import BaseModel, Field

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime, from_iso, from_iso_or_none, utc_now
from charlieverse.types.id import ModelId
from charlieverse.types.lists import TagList, decode_tag_list
from charlieverse.types.strings import NonEmptyString


class KnowledgeId(ModelId):
    pass


class Knowledge(BaseModel):
    """A knowledge/expertise article — domain knowledge that persists across sessions."""

    id: KnowledgeId
    topic: NonEmptyString
    content: NonEmptyString
    tags: TagList | None
    pinned: bool
    created_session_id: SessionId
    updated_session_id: SessionId | None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    deleted_at: UTCDatetime | None

    model_config = {"from_attributes": True}

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> Self:
        return cls.model_construct(
            id=KnowledgeId(row["id"]),
            topic=row["topic"] or "(untitled)",
            content=row["content"],
            tags=decode_tag_list(row["tags"]),
            pinned=bool(row["pinned"]),
            created_session_id=SessionId(row["created_session_id"]),
            updated_session_id=SessionId(row["updated_session_id"]) if row["updated_session_id"] else None,
            created_at=from_iso(row["created_at"]),
            updated_at=from_iso(row["updated_at"]),
            deleted_at=from_iso_or_none(row["deleted_at"]),
        )


class NewKnowledge(BaseModel):
    """Payload for creating a new knowledge article."""

    id: KnowledgeId = Field(default_factory=KnowledgeId)
    topic: NonEmptyString
    content: NonEmptyString
    tags: TagList | None = None
    pinned: bool = False
    created_session_id: SessionId
    created_at: UTCDatetime = Field(default_factory=utc_now)


class UpdateKnowledge(BaseModel):
    """Payload for updating an existing knowledge article."""

    id: KnowledgeId
    topic: NonEmptyString | None = None
    content: NonEmptyString | None = None
    tags: TagList | None = None
    pinned: bool | None = None
    updated_session_id: SessionId | None = None
    updated_at: UTCDatetime = Field(default_factory=utc_now)


class DeleteKnowledge(BaseModel):
    id: KnowledgeId
    deleted_at: UTCDatetime = Field(default_factory=utc_now)
