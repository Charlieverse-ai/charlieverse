"""WorkLog model — tracks technical work details across provider sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from charlieverse.models.entity import NonEmptyString


class WorkLog(BaseModel):
    """A work log entry — captures technical details that sessions don't."""

    id: UUID = Field(default_factory=uuid4)
    content: NonEmptyString
    tags: list[NonEmptyString] | None = None
    created_session_id: UUID
    updated_session_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
