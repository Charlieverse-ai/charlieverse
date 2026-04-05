from __future__ import annotations

import asyncio
import logging

import aiosqlite

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.memory.sessions import SessionId
from charlieverse.types.strings import ShortString

from .models import Message, MessageId, MessageRole

logger = logging.getLogger(__name__)


class MessageStore:
    def __init__(self, db: aiosqlite.Connection) -> None:
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
            (str(msg_id), str(session_id), role.value if isinstance(role, MessageRole) else role, content, created_at),
        )
        inserted = cursor.rowcount > 0
        if inserted:
            row_cursor = await self.db.execute("SELECT rowid FROM messages WHERE id = ?", (str(msg_id),))
            msg_row = await row_cursor.fetchone()
            if msg_row:
                await self.db.execute(
                    "INSERT INTO messages_fts(rowid, content) VALUES(?, ?)",
                    (msg_row[0], content),
                )
        await self.db.commit()
        return inserted

    async def latest(
        self,
        session_id: SessionId | None = None,
        role: MessageRole | str | None = None,
    ) -> Message | None:
        """Return the most recent message, optionally filtered by session and/or role."""
        query = "SELECT * FROM messages WHERE 1=1"
        params: list = []
        if session_id:
            query += " AND session_id = ?"
            params.append(str(session_id))
        if role:
            query += " AND role = ?"
            params.append(role.value if isinstance(role, MessageRole) else role)
        query += " ORDER BY created_at DESC LIMIT 1"

        async with self.db.execute(query, params) as cursor:
            row = await cursor.fetchone()
        return Message.from_row(row) if row else None

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

    async def total(self) -> int:
        """Total rows in messages table."""
        cursor = await self.db.execute("SELECT COUNT(*) FROM messages")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def rebuild(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        await self.db.commit()
