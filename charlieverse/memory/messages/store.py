from __future__ import annotations

import asyncio
import logging

import aiosqlite

from charlieverse.db.fts import sanitize_fts_query
from charlieverse.memory.sessions import SessionId
from charlieverse.types.strings import ShortString

from .models import Message

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
    ) -> list[Message] | None:
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

    async def rebuild(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        await self.db.commit()
