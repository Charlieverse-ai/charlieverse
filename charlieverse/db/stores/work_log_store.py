"""Work log store — CRUD and search for work log entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import aiosqlite

from charlieverse.models import WorkLog


def _tags_json(tags: list[str] | None) -> str | None:
    return json.dumps(tags) if tags else None


def _tags_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parsed = json.loads(raw)
    return parsed if parsed else None


def _row_to_work_log(row: aiosqlite.Row) -> WorkLog:
    return WorkLog(
        id=UUID(row["id"]),
        content=row["content"],
        tags=_tags_list(row["tags"]),
        created_session_id=UUID(row["created_session_id"]),
        updated_session_id=UUID(row["updated_session_id"]) if row["updated_session_id"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class WorkLogStore:
    """Store for work log operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _rebuild_fts(self) -> None:
        """Rebuild FTS index from source table."""
        await self.db.execute("INSERT INTO work_logs_fts(work_logs_fts) VALUES('rebuild')")

    async def create(self, work_log: WorkLog) -> WorkLog:
        """Insert a new work log entry."""
        await self.db.execute(
            """INSERT INTO work_logs (id, content, tags, created_session_id,
               updated_session_id, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(work_log.id),
                work_log.content,
                _tags_json(work_log.tags),
                str(work_log.created_session_id),
                str(work_log.updated_session_id) if work_log.updated_session_id else None,
                work_log.created_at.isoformat(),
                work_log.updated_at.isoformat(),
                work_log.deleted_at.isoformat() if work_log.deleted_at else None,
            ),
        )
        await self._rebuild_fts()
        await self.db.commit()
        return work_log

    async def get(self, work_log_id: UUID) -> WorkLog | None:
        """Fetch a work log by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM work_logs WHERE id = ? AND deleted_at IS NULL",
            (str(work_log_id),),
        )
        row = await cursor.fetchone()
        return _row_to_work_log(row) if row else None

    async def list(
        self,
        session_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WorkLog]:
        """List active work logs, optionally filtered by session."""
        if session_id:
            cursor = await self.db.execute(
                """SELECT * FROM work_logs
                   WHERE created_session_id = ? AND deleted_at IS NULL
                   ORDER BY created_at DESC LIMIT ?""",
                (str(session_id), limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM work_logs WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_work_log(row) for row in await cursor.fetchall()]

    async def for_sessions(self, session_ids: list[UUID]) -> list[WorkLog]:
        """Fetch work logs linked to the given sessions."""
        if not session_ids:
            return []
        placeholders = ",".join("?" * len(session_ids))
        cursor = await self.db.execute(
            f"""SELECT * FROM work_logs
                WHERE created_session_id IN ({placeholders})
                AND deleted_at IS NULL
                ORDER BY created_at DESC""",
            [str(sid) for sid in session_ids],
        )
        return [_row_to_work_log(row) for row in await cursor.fetchall()]

    async def search(self, query: str, limit: int = 10) -> list[WorkLog]:
        """Full-text search across work logs using FTS5 + BM25 ranking."""
        cursor = await self.db.execute(
            """SELECT w.* FROM work_logs w
               JOIN work_logs_fts fts ON w.rowid = fts.rowid
               WHERE work_logs_fts MATCH ?
               AND w.deleted_at IS NULL
               ORDER BY bm25(work_logs_fts)
               LIMIT ?""",
            (query, limit),
        )
        return [_row_to_work_log(row) for row in await cursor.fetchall()]

    async def delete(self, work_log_id: UUID) -> None:
        """Soft-delete a work log entry."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE work_logs SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(work_log_id)),
        )
        await self.db.commit()
