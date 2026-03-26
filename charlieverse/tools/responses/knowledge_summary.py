"""Summary of a knowledge article for search/list responses."""

from uuid import UUID

from pydantic import BaseModel


class KnowledgeSummary(BaseModel):
    """Compact knowledge representation for become_expert and recall results."""

    id: UUID
    content: str
    truncated: bool = False
