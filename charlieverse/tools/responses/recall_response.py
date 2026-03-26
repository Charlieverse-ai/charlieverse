"""Response from the recall tool — entities + knowledge + stories combined."""

from pydantic import BaseModel

from charlieverse.tools.responses.entity_summary import EntitySummary
from charlieverse.tools.responses.knowledge_summary import KnowledgeSummary
from charlieverse.tools.responses.story_summary import StorySummary


class MessageSummary(BaseModel):
    """A message search result."""
    id: str
    role: str
    content: str
    age: str = ""


class RecallResponse(BaseModel):
    """Returned by recall. Merged entity + knowledge + story + message search results."""

    entities: list[EntitySummary]
    knowledge: list[KnowledgeSummary]
    stories: list[StorySummary] = []
    messages: list[MessageSummary] = []
