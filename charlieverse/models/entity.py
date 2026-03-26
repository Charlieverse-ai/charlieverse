"""Entity model — the core memory unit of Charlieverse."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


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

    id: UUID = Field(default_factory=uuid4)
    type: EntityType
    content: NonEmptyString
    tags: list[NonEmptyString] | None = None
    pinned: bool = False
    created_session_id: UUID
    updated_session_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
