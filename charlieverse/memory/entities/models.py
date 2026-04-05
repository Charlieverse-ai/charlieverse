"""Entity model — the core memory unit of Charlieverse.

Entities are the structured memories Charlie stores across sessions: decisions,
solutions, preferences, people, milestones, moments, projects, and events.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from aiosqlite import Row
from pydantic import BaseModel, Field

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime, from_iso, from_iso_or_none, utc_now
from charlieverse.types.id import ModelId
from charlieverse.types.lists import TagList, decode_tag_list
from charlieverse.types.strings import NonEmptyString


class EntityId(ModelId):
    pass


class EntityType(StrEnum):
    """The types of memory entities Charlie can store."""

    decision = "decision"
    solution = "solution"
    preference = "preference"
    person = "person"
    milestone = "milestone"
    moment = "moment"
    project = "project"
    event = "event"


class Entity(BaseModel):
    """A memory entity — decisions, solutions, preferences, people, milestones, moments, projects, events."""

    id: EntityId
    type: EntityType
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
    def from_row(cls, row: Row) -> Self:
        return cls.model_construct(
            id=EntityId(row["id"]),
            type=EntityType(row["type"]),
            content=row["content"],
            tags=decode_tag_list(row["tags"]),
            pinned=bool(row["pinned"]),
            created_session_id=SessionId(row["created_session_id"]),
            updated_session_id=SessionId(row["updated_session_id"]) if row["updated_session_id"] else None,
            created_at=from_iso(row["created_at"]),
            updated_at=from_iso(row["updated_at"]),
            deleted_at=from_iso_or_none(row["deleted_at"]),
        )


class NewEntity(BaseModel):
    """Payload for creating a new entity."""

    id: EntityId = Field(default_factory=EntityId)
    type: EntityType
    content: NonEmptyString
    tags: TagList
    pinned: bool = False
    created_session_id: SessionId
    created_at: UTCDatetime = Field(default_factory=utc_now)


class UpdateEntity(BaseModel):
    """Payload for updating an existing entity. Only set fields are changed."""

    id: EntityId
    content: NonEmptyString | None = None
    tags: TagList | None = None
    pinned: bool | None = None
    updated_session_id: SessionId | None = None
    updated_at: UTCDatetime = Field(default_factory=utc_now)


class DeleteEntity(BaseModel):
    id: EntityId
    deleted_at: UTCDatetime = Field(default_factory=utc_now)
