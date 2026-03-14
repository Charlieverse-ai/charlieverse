"""Session model — tracks conversation sessions across providers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from charlieverse.models.entity import NonEmptyString


class Session(BaseModel):
    """A conversation session with Charlie."""

    id: UUID = Field(default_factory=uuid4)
    what_happened: str | None = None
    for_next_session: str | None = None
    tags: list[NonEmptyString] | None = None
    workspace: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
