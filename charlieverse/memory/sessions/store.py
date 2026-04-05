"""Session store — CRUD for conversation sessions."""

from __future__ import annotations

import builtins
import re

import aiosqlite

from charlieverse.models import ContextMessage
from charlieverse.types.dates import UTCDatetime, from_iso

from .models import DeleteSession, NewSession, Session, SessionId, UpdateSession

# Messages that are session-save machinery, not conversation
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^/trick\s+session-save", re.IGNORECASE),
    re.compile(r"^/session-save", re.IGNORECASE),
    re.compile(r"^/trick\s+Charlieverse:session-save", re.IGNORECASE),
    re.compile(r"<task-notification>", re.IGNORECASE),
    re.compile(r"<system-reminder>", re.IGNORECASE),
]


def _is_noise(content: str) -> bool:
    """Return True if the message is session-save machinery or system noise."""
    stripped = content.strip()
    return any(p.search(stripped) for p in _NOISE_PATTERNS)


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
            (str(session.id), session.workspace, session.created_at, session.created_at),
        )
        await self.db.commit()

        return session.id

    async def get(self, session_id: SessionId) -> Session | None:
        """Fetch a session by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ? AND deleted_at IS NULL",
            [str(session_id)],
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
            [*values, str(session.id)],
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

    async def recent_messages(self, turns: int = 3) -> list[ContextMessage]:
        """Fetch the last N turns of conversation globally.

        A "turn" is a user message + the assistant reply that follows it.
        Filters out session-save commands, system-reminders, and task-notifications.
        Returns messages in chronological order (oldest first).

        Note: not scoped by session_id because the session ID on messages
        may differ from the session ID on session_update saves.
        """
        # Grab more than we need so we can filter noise and still hit the turn count
        fetch_limit = turns * 6  # generous buffer for filtered messages
        cursor = await self.db.execute(
            """SELECT role, content, created_at FROM messages
               ORDER BY created_at DESC
               LIMIT ?""",
            (fetch_limit,),
        )
        rows = await cursor.fetchall()

        # Filter noise, collect turns (walking backwards from most recent)
        filtered: list[ContextMessage] = []
        for row in rows:
            content = row["content"] or ""
            if _is_noise(content):
                continue
            filtered.append(
                ContextMessage(
                    role=row["role"],
                    content=content,
                    created_at=from_iso(row["created_at"]),
                )
            )

        # Count user messages to determine turns, take the last N turns
        user_count = 0
        cutoff = 0
        for i, msg in enumerate(filtered):
            if msg.role == "user":
                user_count += 1
                if user_count > turns:
                    cutoff = i
                    break

        result = filtered[:cutoff] if cutoff else filtered
        # Reverse to chronological order
        result.reverse()
        return result

    async def delete(self, session: DeleteSession) -> None:
        """Mark a session as deleted."""
        await self.db.execute(
            "UPDATE sessions SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (session.deleted_at, str(session.id)),
        )
        await self.db.commit()

    async def messages_for_session(
        self,
        session_id: SessionId,
        since: UTCDatetime | None = None,
    ) -> builtins.list[ContextMessage]:
        """Fetch all messages for a session, optionally after a cutoff."""
        if since is not None:
            cursor = await self.db.execute(
                """SELECT role, content, created_at FROM messages
                   WHERE session_id = ? AND created_at > ?
                   ORDER BY created_at ASC""",
                (str(session_id), since.isoformat()),
            )
        else:
            cursor = await self.db.execute(
                """SELECT role, content, created_at FROM messages
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (str(session_id),),
            )
        return [
            ContextMessage(
                role=row["role"],
                content=row["content"] or "",
                created_at=from_iso(row["created_at"]),
            )
            for row in await cursor.fetchall()
        ]
