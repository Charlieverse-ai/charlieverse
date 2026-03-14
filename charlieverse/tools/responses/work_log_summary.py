"""Summary of a work log entry for list/search responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WorkLogSummary(BaseModel):
    """Compact work log representation."""

    id: UUID
    content: str
    tags: list[str] | None = None
    session_id: UUID
    created_at: datetime
