from pydantic import BaseModel


class Stats(BaseModel):
    """Dashboard stats — counts of entities by type, sessions, and knowledge."""

    entities: dict[str, int]
    sessions: int
    knowledge: int
