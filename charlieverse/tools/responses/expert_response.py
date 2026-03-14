"""Response from the become_expert tool."""

from pydantic import BaseModel

from charlieverse.tools.responses.knowledge_summary import KnowledgeSummary


class ExpertResponse(BaseModel):
    """Returned by become_expert. Knowledge articles matching the query."""

    articles: list[KnowledgeSummary]
