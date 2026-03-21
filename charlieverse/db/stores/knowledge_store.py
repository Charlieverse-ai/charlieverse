"""Knowledge store — CRUD and search for expertise articles."""

from __future__ import annotations

import aiosqlite

from datetime import datetime, timezone
from uuid import UUID
from typing import List

from charlieverse.db.stores._utils import _tags_json, _tags_list
from charlieverse.models import Knowledge


def _row_to_knowledge(row: aiosqlite.Row) -> Knowledge:
    return Knowledge(
        id=UUID(row["id"]),
        topic=row["topic"] or "(untitled)",
        content=row["content"],
        tags=_tags_list(row["tags"]),
        pinned=bool(row["pinned"]),
        created_session_id=UUID(row["created_session_id"]),
        updated_session_id=UUID(row["updated_session_id"]) if row["updated_session_id"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class KnowledgeStore:
    """Store for knowledge/expertise article operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _sync_fts_insert(self, knowledge: Knowledge) -> None:
        """Insert a new knowledge article into the FTS index."""
        cursor = await self.db.execute(
            "SELECT rowid FROM knowledge WHERE id = ?", (str(knowledge.id),)
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO knowledge_fts(rowid, topic, content, tags) VALUES(?, ?, ?, ?)",
            (row[0], knowledge.topic, knowledge.content, _tags_json(knowledge.tags) or ""),
        )

    async def _sync_fts_delete(self, knowledge_id: UUID) -> None:
        """Remove a knowledge article's current FTS entry using values from the content table."""
        cursor = await self.db.execute(
            "SELECT rowid, topic, content, tags FROM knowledge WHERE id = ?", (str(knowledge_id),)
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, tags) VALUES('delete', ?, ?, ?, ?)",
            (row[0], row[1], row[2], row[3] or ""),
        )

    async def rebuild_fts(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all knowledge embeddings from scratch.

        Drops and recreates the vec table to avoid corruption from partial
        writes on the vec0 virtual table.
        """
        from charlieverse.embeddings import encode
        from sqlite_vec import serialize_float32

        articles = await self.list(limit=5000)
        if not articles:
            return

        texts = [f"{article.topic} {article.content}" for article in articles]
        embeddings = await encode(texts)

        rows: list[tuple[int, bytes]] = []
        for article, embedding in zip(articles, embeddings):
            try:
                cursor = await self.db.execute(
                    "SELECT rowid FROM knowledge WHERE id = ?", (str(article.id),)
                )
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                continue

        await self.db.execute("DROP TABLE IF EXISTS knowledge_vec")
        await self.db.execute(
            "CREATE VIRTUAL TABLE knowledge_vec USING vec0(embedding float[384])"
        )
        for rowid, embedding in rows:
            await self.db.execute(
                "INSERT INTO knowledge_vec(rowid, embedding) VALUES(?, ?)",
                (rowid, embedding),
            )
        await self.db.commit()

    async def create(self, knowledge: Knowledge) -> Knowledge:
        """Insert a new knowledge article."""
        await self.db.execute(
            """INSERT INTO knowledge (id, topic, content, tags, pinned, created_session_id,
               updated_session_id, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(knowledge.id),
                knowledge.topic,
                knowledge.content,
                _tags_json(knowledge.tags),
                int(knowledge.pinned),
                str(knowledge.created_session_id),
                str(knowledge.updated_session_id) if knowledge.updated_session_id else None,
                knowledge.created_at.isoformat(),
                knowledge.updated_at.isoformat(),
                knowledge.deleted_at.isoformat() if knowledge.deleted_at else None,
            ),
        )
        await self._sync_fts_insert(knowledge)
        await self.db.commit()
        return knowledge

    async def get(self, knowledge_id: UUID) -> Knowledge | None:
        """Fetch a knowledge article by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE id = ? AND deleted_at IS NULL",
            (str(knowledge_id),),
        )
        row = await cursor.fetchone()
        return _row_to_knowledge(row) if row else None

    async def find_by_topic(self, topic: str) -> Knowledge | None:
        """Find a knowledge article by exact topic match."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE topic = ? AND deleted_at IS NULL",
            (topic,),
        )
        row = await cursor.fetchone()
        return _row_to_knowledge(row) if row else None

    async def upsert(self, knowledge: Knowledge) -> Knowledge:
        """Insert or update a knowledge article by topic."""
        existing = await self.find_by_topic(knowledge.topic)
        if existing:
            now = datetime.now(timezone.utc)
            # Delete old FTS entry BEFORE updating (needs old values from content table)
            await self._sync_fts_delete(existing.id)
            await self.db.execute(
                """UPDATE knowledge SET content = ?, tags = ?, pinned = ?,
                   updated_session_id = ?, updated_at = ?
                   WHERE id = ? AND deleted_at IS NULL""",
                (
                    knowledge.content,
                    _tags_json(knowledge.tags),
                    int(knowledge.pinned),
                    str(knowledge.updated_session_id) if knowledge.updated_session_id else None,
                    now.isoformat(),
                    str(existing.id),
                ),
            )
            # Insert new FTS entry AFTER updating
            existing.content = knowledge.content
            existing.tags = knowledge.tags
            await self._sync_fts_insert(existing)
            await self.db.commit()
            return existing
        return await self.create(knowledge)

    async def list(self, limit: int = 50) -> List[Knowledge]:
        """List active knowledge articles."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_knowledge(row) for row in await cursor.fetchall()]

    async def pinned(self) -> List[Knowledge]:
        """Fetch all pinned, active knowledge articles."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE pinned = 1 AND deleted_at IS NULL ORDER BY topic",
        )
        return [_row_to_knowledge(row) for row in await cursor.fetchall()]

    async def delete(self, knowledge_id: UUID) -> None:
        """Soft-delete a knowledge article."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE knowledge SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(knowledge_id)),
        )
        await self.db.commit()

    async def pin(self, knowledge_id: UUID, pinned: bool) -> None:
        """Set the pinned state of a knowledge article."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE knowledge SET pinned = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (int(pinned), now.isoformat(), str(knowledge_id)),
        )
        await self.db.commit()

    async def search(self, query: str, limit: int = 10) -> List[Knowledge]:
        """Full-text search across knowledge using FTS5 + BM25 ranking."""
        from charlieverse.db.fts import sanitize_fts_query

        fts_query = sanitize_fts_query(query)
        if not fts_query:
            return []

        cursor = await self.db.execute(
            """SELECT k.* FROM knowledge k
               JOIN knowledge_fts fts ON k.rowid = fts.rowid
               WHERE knowledge_fts MATCH ?
               AND k.deleted_at IS NULL
               ORDER BY bm25(knowledge_fts)
               LIMIT ?""",
            (fts_query, limit),
        )
        return [_row_to_knowledge(row) for row in await cursor.fetchall()]

    async def search_by_vector(self, embedding: List[float], limit: int = 10) -> List[Knowledge]:
        """Semantic search using sqlite-vec."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute(
            """SELECT k.*, v.distance FROM knowledge k
               JOIN knowledge_vec v ON k.rowid = v.rowid
               WHERE v.embedding MATCH ?
               AND v.k = ?
               AND k.deleted_at IS NULL
               ORDER BY v.distance
               LIMIT ?""",
            (serialize_float32(embedding), limit, limit),
        )
        return [_row_to_knowledge(row) for row in await cursor.fetchall()]

    async def upsert_embedding(self, knowledge_id: UUID, embedding: List[float]) -> None:
        """Store or update the embedding for a knowledge article."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute(
            "SELECT rowid FROM knowledge WHERE id = ?", (str(knowledge_id),)
        )
        row = await cursor.fetchone()
        if not row:
            return

        rowid = row[0]
        await self.db.execute("DELETE FROM knowledge_vec WHERE rowid = ?", (rowid,))
        await self.db.execute(
            "INSERT INTO knowledge_vec(rowid, embedding) VALUES (?, ?)",
            (rowid, serialize_float32(embedding)),
        )
        await self.db.commit()
