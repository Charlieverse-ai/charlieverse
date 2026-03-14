"""Knowledge model — persistent expertise articles that grow over time."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from charlieverse.models.entity import NonEmptyString


class Knowledge(BaseModel):
    """A knowledge/expertise article — domain knowledge that persists across sessions."""

    id: UUID = Field(default_factory=uuid4)
    topic: NonEmptyString
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
