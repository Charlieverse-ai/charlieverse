"""Session store — CRUD for conversation sessions."""

from __future__ import annotations

import aiosqlite

from .models import DeleteSession, NewSession, Session, SessionId, UpdateSession


class SessionError(Exception):
    """An error in the Session Store."""


class SessionStore:
    """Store for session operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, session: NewSession) -> SessionId:
        """Insert a new session."""
        await self.db.execute(
            "INSERT INTO sessions (id, workspace, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session.id, session.workspace, session.created_at, session.created_at),
        )
        await self.db.commit()

        return session.id

    async def get(self, session_id: SessionId) -> Session | None:
        """Fetch a session by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ? AND deleted_at IS NULL",
            [session_id],
        )
        row = await cursor.fetchone()
        return Session.from_row(row) if row else None

    async def update(self, session: UpdateSession) -> Session:
        """Update an existing session."""

        columns: list[str] = []
        values: list = []

        if session.content:
            values.append(session.content.what_happened)
            columns.append("what_happened = ?")

            values.append(session.content.for_next_session)
            columns.append("for_next_session = ?")

        if session.tags:
            values.append(session.tag_value())
            columns.append("tags = ?")

        values.append(session.workspace)
        columns.append("workspace = ?")

        values.append(session.updated_at.isoformat())
        columns.append("updated_at = ?")
        statements = ", ".join(columns)

        cursor = await self.db.execute(
            f"UPDATE sessions SET {statements} WHERE id = ? AND deleted_at IS NULL RETURNING *",
            [*values, session.id],
        )
        row = await cursor.fetchone()
        await self.db.commit()

        if not row:
            raise SessionError("Could not fetch session after updating")

        return Session.from_row(row)

    async def upsert(self, session: UpdateSession) -> Session:
        """Insert or update a session by ID."""
        if not await self.get(session.id):
            await self.create(NewSession.from_update(session))

        return await self.update(session)

    async def recent(
        self,
        limit: int = 10,
        workspace: str | None = None,
    ) -> list[Session]:
        """Fetch recent sessions. Workspace is stored as metadata but does not filter results."""
        cursor = await self.db.execute(
            """SELECT * FROM sessions
               WHERE what_happened IS NOT NULL
               AND for_next_session IS NOT NULL
               AND deleted_at IS NULL
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )
        return [Session.from_row(row) for row in await cursor.fetchall()]

    async def recent_within_days(
        self,
        days: int = 2,
        workspace: str | None = None,
    ) -> list[Session]:
        """Fetch sessions from the last N days with content. Workspace is metadata, not a filter."""
        cursor = await self.db.execute(
            """SELECT * FROM sessions
               WHERE what_happened IS NOT NULL
               AND for_next_session IS NOT NULL
               AND deleted_at IS NULL
               AND DATE(created_at, 'localtime') >= DATE('now', 'localtime', ?)
               ORDER BY created_at DESC""",
            (f"-{days} days",),
        )
        return [Session.from_row(row) for row in await cursor.fetchall()]

    async def recent_within_range(
        self,
        range_start: str,
        range_end: str,
        workspace: str | None = None,
    ) -> list[Session]:
        """Fetch sessions within a date range. Workspace is metadata, not a filter."""
        cursor = await self.db.execute(
            """SELECT * FROM sessions
               WHERE what_happened IS NOT NULL
               AND for_next_session IS NOT NULL
               AND deleted_at IS NULL
               AND DATE(created_at, 'localtime') >= ?
               AND DATE(created_at, 'localtime') <= ?
               ORDER BY created_at DESC""",
            (range_start, range_end),
        )
        return [Session.from_row(row) for row in await cursor.fetchall()]

    async def delete(self, session: DeleteSession) -> None:
        """Mark a session as deleted."""
        await self.db.execute(
            "UPDATE sessions SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (session.deleted_at, session.id),
        )
        await self.db.commit()

    async def count_with_summary(self) -> int:
        """Count of non-deleted sessions that have a what_happened summary."""
        cursor = await self.db.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NULL AND what_happened IS NOT NULL")
        row = await cursor.fetchone()
        return row[0] if row else 0
