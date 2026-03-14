"""Summary of an entity for search/list responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EntitySummary(BaseModel):
    """Compact entity representation for recall and list results."""

    id: UUID
    type: str
    content: str
    tags: list[str] | None = None
    pinned: bool = False
    created_at: datetime
