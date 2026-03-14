"""Entity model — the core memory unit of Charlieverse."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class EntityType(StrEnum):
    """The six types of memory entities Charlie can store."""

    decision = "decision"
    solution = "solution"
    preference = "preference"
    person = "person"
    milestone = "milestone"
    moment = "moment"

    @property
    def is_workspace_scoped(self) -> bool:
        """Whether this entity type is scoped to a workspace.

        Personality types (moment, preference, person) are always global.
        Technical types (decision, solution, milestone) are workspace-scoped.
        """
        match self:
            case EntityType.moment | EntityType.preference | EntityType.person:
                return False
            case EntityType.decision | EntityType.solution | EntityType.milestone:
                return True


class Entity(BaseModel):
    """A memory entity — decisions, solutions, preferences, people, milestones, moments."""

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
