"""Story model — tiered narrative arcs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class StoryTier(StrEnum):
    session = "session"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    all_time = "all-time"

@dataclass
class Story:
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    summary: str | None = None
    content: str = ""
    tier: StoryTier = StoryTier.weekly
    period_start: str | None = None
    period_end: str | None = None
    workspace: str | None = None
    session_id: UUID | None = None
    tags: list[str] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
