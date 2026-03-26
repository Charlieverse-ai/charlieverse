"""Session store — CRUD for conversation sessions."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

import aiosqlite

from charlieverse.db.stores._utils import _tags_json, _tags_list
from charlieverse.models import ContextMessage, Session

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


def _row_to_session(row: aiosqlite.Row) -> Session:
    return Session(
        id=UUID(row["id"]),
        what_happened=row["what_happened"],
        for_next_session=row["for_next_session"],
        tags=_tags_list(row["tags"]),
        workspace=row["workspace"],
        transcript_path=row["transcript_path"] if "transcript_path" in row.keys() else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class SessionStore:
    """Store for session operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, session: Session) -> Session:
        """Insert a new session."""
        await self.db.execute(
            """INSERT INTO sessions (id, what_happened, for_next_session, tags, workspace,
               transcript_path, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(session.id),
                session.what_happened,
                session.for_next_session,
                _tags_json(session.tags),
                session.workspace,
                session.transcript_path,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.deleted_at.isoformat() if session.deleted_at else None,
            ),
        )
        await self.db.commit()
        return session

    async def get(self, session_id: UUID) -> Session | None:
        """Fetch a session by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ? AND deleted_at IS NULL",
            (str(session_id),),
        )
        row = await cursor.fetchone()
        return _row_to_session(row) if row else None

    async def update(self, session: Session) -> Session:
        """Update an existing session."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            """UPDATE sessions SET what_happened = ?, for_next_session = ?,
               tags = ?, workspace = ?, transcript_path = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL""",
            (
                session.what_happened,
                session.for_next_session,
                _tags_json(session.tags),
                session.workspace,
                session.transcript_path,
                now.isoformat(),
                str(session.id),
            ),
        )
        await self.db.commit()
        return session

    async def upsert(self, session: Session) -> Session:
        """Insert or update a session by ID."""
        existing = await self.get(session.id)
        if existing:
            return await self.update(session)
        return await self.create(session)

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
        return [_row_to_session(row) for row in await cursor.fetchall()]

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
        return [_row_to_session(row) for row in await cursor.fetchall()]

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
        return [_row_to_session(row) for row in await cursor.fetchall()]

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
            filtered.append(ContextMessage(
                role=row["role"],
                content=content,
                created_at=datetime.fromisoformat(row["created_at"]),
            ))

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

    async def delete(self, session_id: UUID) -> None:
        """Soft-delete a session."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE sessions SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(session_id)),
        )
        await self.db.commit()
