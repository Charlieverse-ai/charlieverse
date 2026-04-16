"""Response from the recall tool — entities + knowledge + stories combined."""

from __future__ import annotations

from pydantic import BaseModel

from charlieverse.memory.knowledge import KnowledgeId


class KnowledgeSummary(BaseModel):
    """Compact knowledge representation."""

    id: KnowledgeId
    content: str
    truncated: bool = False
