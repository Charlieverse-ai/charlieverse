from pydantic import BaseModel

from charlieverse.memory.entities import Entity
from charlieverse.memory.knowledge import Knowledge


class SearchResults(BaseModel):
    """Unified search results across entities and knowledge."""

    memories: list[Entity]
    knowledge: list[Knowledge]
