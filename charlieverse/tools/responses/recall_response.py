"""Response from the recall tool — entities + knowledge combined."""

from pydantic import BaseModel

from charlieverse.tools.responses.entity_summary import EntitySummary
from charlieverse.tools.responses.knowledge_summary import KnowledgeSummary


class RecallResponse(BaseModel):
    """Returned by recall. Merged entity + knowledge search results."""

    entities: list[EntitySummary]
    knowledge: list[KnowledgeSummary]
