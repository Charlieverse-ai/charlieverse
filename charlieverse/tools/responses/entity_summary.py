"""Summary of an entity for search/list responses."""

from uuid import UUID

from pydantic import BaseModel


class EntitySummary(BaseModel):
    """Compact entity representation for recall and list results."""

    id: UUID
    type: str
    content: str
    age: str = ""
    truncated: bool = False
