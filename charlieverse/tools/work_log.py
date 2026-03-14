"""Work log tools — log_work, list_work_logs, search_work_logs."""

from __future__ import annotations

from uuid import UUID

from charlieverse.db.stores import WorkLogStore
from charlieverse.models import WorkLog
from charlieverse.tools.responses import IdResponse, WorkLogSummary, WorkLogsResponse


def _to_summary(w: WorkLog) -> WorkLogSummary:
    return WorkLogSummary(
        id=w.id,
        content=w.content,
        tags=w.tags,
        session_id=w.created_session_id,
        created_at=w.created_at,
    )


async def log_work(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    *,
    work_logs: WorkLogStore,
) -> IdResponse:
    """Log a work entry — captures technical details."""
    entry = WorkLog(
        content=content,
        tags=tags,
        created_session_id=UUID(session_id) if session_id else UUID(int=0),
    )
    entry = await work_logs.create(entry)
    return IdResponse(id=entry.id)


async def list_work_logs(
    session_id: str | None = None,
    limit: int = 20,
    *,
    work_logs: WorkLogStore,
) -> WorkLogsResponse:
    """List work log entries, optionally filtered by session."""
    sid = UUID(session_id) if session_id else None
    entries = await work_logs.list(session_id=sid, limit=limit)
    return WorkLogsResponse(work_logs=[_to_summary(w) for w in entries])


async def search_work_logs(
    query: str,
    limit: int = 10,
    *,
    work_logs: WorkLogStore,
) -> WorkLogsResponse:
    """Search work logs using full-text search."""
    entries = await work_logs.search(query, limit=limit)
    return WorkLogsResponse(work_logs=[_to_summary(w) for w in entries])
