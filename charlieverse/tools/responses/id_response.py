"""Response returned when a single entity is created."""

from uuid import UUID

from pydantic import BaseModel


class IdResponse(BaseModel):
    """Returned by remember_*, update_expertise, log_work."""

    id: UUID
