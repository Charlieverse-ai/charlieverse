"""Summary of a story returned in recall results."""

from pydantic import BaseModel


class StorySummary(BaseModel):
    """A story search result — truncated content for recall."""

    id: str
    title: str
    tier: str
    summary: str | None = None
    truncated: bool = False
