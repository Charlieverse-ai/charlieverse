"""Response from the recall tool — entities + knowledge combined."""

from pydantic import BaseModel

from charlieverse.tools.responses.entity_summary import EntitySummary
from charlieverse.tools.responses.knowledge_summary import KnowledgeSummary


class MessageSummary(BaseModel):
    """A message search result."""
    id: str
    role: str
    content: str
    created_at: str


class RecallResponse(BaseModel):
    """Returned by recall. Merged entity + knowledge + message search results."""

    entities: list[EntitySummary]
    knowledge: list[KnowledgeSummary]
    messages: list[MessageSummary] = []
