"""Session tools — session_update"""

from __future__ import annotations

from uuid import UUID

from charlieverse.db.stores import SessionStore
from charlieverse.models import Session
from charlieverse.tools.responses import AckResponse


async def session_update(
    id: str,
    what_happened: str,
    for_next_session: str,
    tags: list[str] | None = None,
    workspace: str | None = None,
    *,
    sessions: SessionStore,
) -> AckResponse:
    """Save a detailed snapshot of the current session."""
    session = await sessions.get(UUID(id))
    if session:
        session.what_happened = what_happened
        session.for_next_session = for_next_session
        session.tags = tags
        if workspace is not None:
            session.workspace = workspace
        await sessions.update(session)
    else:
        session = Session(
            id=UUID(id),
            what_happened=what_happened,
            for_next_session=for_next_session,
            tags=tags,
            workspace=workspace,
        )
        await sessions.create(session)
    return AckResponse()
