from __future__ import annotations

import asyncio
import logging
import re

from aiosqlite import Connection

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime
from charlieverse.types.strings import ShortString

from .models import LatestMessage, Message, MessageId, MessageRole

logger = logging.getLogger(__name__)


class MessageStore:
    def __init__(self, db: Connection) -> None:
        self.db = db
        self._vec_lock = asyncio.Lock()

    async def search(
        self,
        query: ShortString,
        limit: int = 20,
        session_id: SessionId | None = None,
    ) -> list[Message]:
        """Search past messages in conversations. Returns matching messages with role and date."""

        safe_query = sanitize_fts_query(query)
        if not safe_query:
            return []
        if session_id:
            cursor = await self.db.execute(
                """SELECT m.* FROM messages m
                    JOIN messages_fts fts ON m.rowid = fts.rowid
                    WHERE messages_fts MATCH ? AND m.session_id = ?
                    ORDER BY RANK LIMIT ?""",
                (safe_query, session_id, limit),
            )
        else:
            cursor = await self.db.execute(
                """SELECT m.* FROM messages m
                    JOIN messages_fts fts ON m.rowid = fts.rowid
                    WHERE messages_fts MATCH ?
                    ORDER BY RANK LIMIT ?""",
                (safe_query, limit),
            )
        return [Message.from_row(row) for row in await cursor.fetchall()]

    async def save(
        self,
        msg_id: MessageId,
        session_id: SessionId,
        role: MessageRole,
        content: str,
        created_at: str,
    ) -> bool:
        """Insert a message, sync FTS. Returns True if a new row was written (False on dedupe)."""
        cursor = await self.db.execute(
            """INSERT OR IGNORE INTO messages (id, session_id, role, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (msg_id, session_id, role.value if isinstance(role, MessageRole) else role, content, created_at),
        )
        inserted = cursor.rowcount > 0
        if inserted:
            row_cursor = await self.db.execute("SELECT rowid FROM messages WHERE id = ?", (msg_id,))
            msg_row = await row_cursor.fetchone()
            if msg_row:
                await self.db.execute(
                    "INSERT INTO messages_fts(rowid, content) VALUES(?, ?)",
                    (msg_row[0], content),
                )
        await self.db.commit()
        return inserted

    async def recent_messages(self, turns: int = 3) -> list[Message]:
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
            """SELECT * FROM messages
               ORDER BY created_at DESC
               LIMIT ?""",
            (fetch_limit,),
        )
        messages = [Message.from_row(row) for row in await cursor.fetchall()]

        # Filter noise, collect turns (walking backwards from most recent)
        filtered: list[Message] = []
        for row in messages:
            if _is_noise(row.content):
                continue
            filtered.append(row)

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

    async def messages_for_session(
        self,
        session_id: SessionId,
        since: UTCDatetime | None = None,
    ) -> list[Message]:
        """Fetch all messages for a session, optionally after a cutoff."""
        if since is not None:
            cursor = await self.db.execute(
                """SELECT * FROM messages
                   WHERE session_id = ? AND created_at > ?
                   ORDER BY created_at ASC""",
                (session_id, since.isoformat()),
            )
        else:
            cursor = await self.db.execute(
                """SELECT * FROM messages
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,),
            )

        return [Message.from_row(row) for row in await cursor.fetchall()]

    async def latest(
        self,
        session_id: SessionId | None = None,
        role: MessageRole | str | None = None,
    ) -> LatestMessage | None:
        """Return the most recent message, optionally filtered by session and/or role."""
        query = "SELECT * FROM messages WHERE 1=1"
        params: list = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if role:
            query += " AND role = ?"
            params.append(role.value if isinstance(role, MessageRole) else role)
        query += " ORDER BY created_at DESC LIMIT 1"

        async with self.db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            count = await self.total(session_id)
            if row:
                message = LatestMessage.from_row(row)
                message.message_count = count
                return message

    async def bulk_insert(self, batch: list[tuple]) -> int:
        """Bulk insert (id, session_id, role, content, created_at) tuples. Returns rows actually inserted."""
        before = await self.total()
        await self.db.executemany(
            """INSERT OR IGNORE INTO messages (id, session_id, role, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            batch,
        )
        await self.db.commit()
        after = await self.total()
        return after - before

    async def total(self, session_id: SessionId | None = None) -> int:
        """Total rows in messages table."""
        if session_id:
            cursor = await self.db.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", [session_id])
        else:
            cursor = await self.db.execute("SELECT COUNT(*) FROM messages")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def rebuild(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        await self.db.commit()


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
