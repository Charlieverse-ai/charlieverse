"""Acknowledgement response for operations that don't return data."""

from pydantic import BaseModel


class AckResponse(BaseModel):
    """Returned by session_update, forget, pin. Non-conversational confirmation."""

    saved: bool = True
