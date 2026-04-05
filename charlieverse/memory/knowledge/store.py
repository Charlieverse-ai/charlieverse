"""Knowledge store — CRUD, search, and maintenance for expertise articles.

This is the only place knowledge is queried.
"""

from __future__ import annotations

import asyncio
import builtins
import logging

import aiosqlite

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime
from charlieverse.types.lists import encode_tag_list

from .models import DeleteKnowledge, Knowledge, KnowledgeId, NewKnowledge, UpdateKnowledge

logger = logging.getLogger(__name__)


class KnowledgeError(Exception):
    """An error in the Knowledge Store."""


class KnowledgeStore:
    """Store for knowledge/expertise article operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db
        self._vec_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, knowledge: NewKnowledge) -> Knowledge:
        """Insert a new knowledge article."""
        await self.db.execute(
            """INSERT INTO knowledge (id, topic, content, tags, pinned, created_session_id,
               updated_session_id, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(knowledge.id),
                knowledge.topic,
                knowledge.content,
                encode_tag_list(knowledge.tags) if knowledge.tags else None,
                int(knowledge.pinned),
                str(knowledge.created_session_id),
                None,
                knowledge.created_at.isoformat(),
                knowledge.created_at.isoformat(),
                None,
            ),
        )
        created = await self.get(knowledge.id)
        if not created:
            raise KnowledgeError("Could not fetch knowledge after creating")
        await self._sync_fts_insert(created)
        await self.db.commit()
        return created

    async def update(self, update: UpdateKnowledge) -> Knowledge:
        """Update an existing knowledge article. Only set fields are changed."""
        existing = await self.get(update.id)
        if not existing:
            raise KnowledgeError(f"Knowledge article {update.id!s} not found")

        merged_topic = update.topic if update.topic is not None else existing.topic
        merged_content = update.content if update.content is not None else existing.content
        merged_tags = update.tags if update.tags is not None else existing.tags
        merged_pinned = update.pinned if update.pinned is not None else existing.pinned
        merged_updated_session = (
            update.updated_session_id
            if update.updated_session_id is not None
            else existing.updated_session_id
        )

        await self._sync_fts_delete(update.id)
        cursor = await self.db.execute(
            """UPDATE knowledge SET topic = ?, content = ?, tags = ?, pinned = ?,
               updated_session_id = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL RETURNING *""",
            (
                merged_topic,
                merged_content,
                encode_tag_list(merged_tags) if merged_tags else None,
                int(merged_pinned),
                str(merged_updated_session) if merged_updated_session else None,
                update.updated_at.isoformat(),
                str(update.id),
            ),
        )
        row = await cursor.fetchone()
        if not row:
            raise KnowledgeError("Could not fetch knowledge after updating")

        updated = Knowledge.from_row(row)
        await self._sync_fts_insert(updated)
        await self.db.commit()
        return updated

    async def upsert(self, knowledge: NewKnowledge) -> Knowledge:
        """Insert or update a knowledge article by topic match."""
        existing = await self.find_by_topic(knowledge.topic)
        if existing:
            return await self.update(
                UpdateKnowledge(
                    id=existing.id,
                    topic=knowledge.topic,
                    content=knowledge.content,
                    tags=knowledge.tags,
                    pinned=knowledge.pinned,
                    updated_session_id=knowledge.created_session_id,
                )
            )
        return await self.create(knowledge)

    async def get(self, knowledge_id: KnowledgeId) -> Knowledge | None:
        """Fetch a knowledge article by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE id = ? AND deleted_at IS NULL",
            (str(knowledge_id),),
        )
        row = await cursor.fetchone()
        return Knowledge.from_row(row) if row else None

    async def find_by_topic(self, topic: str) -> Knowledge | None:
        """Find a knowledge article by exact topic match."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE topic = ? AND deleted_at IS NULL",
            (topic,),
        )
        row = await cursor.fetchone()
        return Knowledge.from_row(row) if row else None

    async def list(self, limit: int = 50) -> builtins.list[Knowledge]:
        """List active knowledge articles."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def pinned(self) -> builtins.list[Knowledge]:
        """Fetch all pinned, active knowledge articles."""
        cursor = await self.db.execute(
            "SELECT * FROM knowledge WHERE pinned = 1 AND deleted_at IS NULL ORDER BY topic",
        )
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def for_session(self, session_id: SessionId) -> builtins.list[Knowledge]:
        """Fetch active knowledge articles created within a single session."""
        cursor = await self.db.execute(
            """SELECT * FROM knowledge
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (str(session_id),),
        )
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def created_since(self, since: UTCDatetime) -> builtins.list[Knowledge]:
        """Fetch active knowledge articles created at or after the given timestamp."""
        cursor = await self.db.execute(
            """SELECT * FROM knowledge
               WHERE deleted_at IS NULL AND created_at >= ?
               ORDER BY created_at ASC""",
            (since.isoformat(),),
        )
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def delete(self, delete: DeleteKnowledge) -> None:
        """Soft-delete a knowledge article."""
        await self.db.execute(
            "UPDATE knowledge SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (delete.deleted_at.isoformat(), delete.deleted_at.isoformat(), str(delete.id)),
        )
        await self.db.commit()

    async def pin(self, knowledge_id: KnowledgeId, pinned: bool) -> None:
        """Set the pinned state of a knowledge article."""
        from charlieverse.types.dates import utc_now

        now = utc_now()
        await self.db.execute(
            "UPDATE knowledge SET pinned = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (int(pinned), now.isoformat(), str(knowledge_id)),
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str, limit: int = 10) -> builtins.list[Knowledge]:
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
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def search_by_vector(
        self,
        embedding: builtins.list[float],
        limit: int = 10,
    ) -> builtins.list[Knowledge]:
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
        return [Knowledge.from_row(row) for row in await cursor.fetchall()]

    async def upsert_embedding(
        self,
        knowledge_id: KnowledgeId,
        embedding: builtins.list[float],
    ) -> None:
        """Store or update the embedding for a knowledge article."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute(
            "SELECT rowid FROM knowledge WHERE id = ?",
            (str(knowledge_id),),
        )
        row = await cursor.fetchone()
        if not row:
            return

        rowid = row[0]
        async with self._vec_lock:
            await self.db.execute("DELETE FROM knowledge_vec WHERE rowid = ?", (rowid,))
            await self.db.execute(
                "INSERT INTO knowledge_vec(rowid, embedding) VALUES (?, ?)",
                (rowid, serialize_float32(embedding)),
            )
            await self.db.commit()

    # ------------------------------------------------------------------
    # FTS sync (internal)
    # ------------------------------------------------------------------

    async def _sync_fts_insert(self, knowledge: Knowledge) -> None:
        cursor = await self.db.execute(
            "SELECT rowid FROM knowledge WHERE id = ?",
            (str(knowledge.id),),
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO knowledge_fts(rowid, topic, content, tags) VALUES(?, ?, ?, ?)",
            (
                row[0],
                knowledge.topic,
                knowledge.content,
                encode_tag_list(knowledge.tags) if knowledge.tags else "",
            ),
        )

    async def _sync_fts_delete(self, knowledge_id: KnowledgeId) -> None:
        cursor = await self.db.execute(
            "SELECT rowid, topic, content, tags FROM knowledge WHERE id = ?",
            (str(knowledge_id),),
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, tags) VALUES('delete', ?, ?, ?, ?)",
            (row[0], row[1], row[2], row[3] or ""),
        )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def rebuild(self) -> None:
        from asyncio import gather

        await gather(self.rebuild_fts(), self.rebuild_vec())

    async def rebuild_fts(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all knowledge embeddings from scratch."""
        from sqlite_vec import serialize_float32

        from charlieverse.embeddings import encode

        articles = await self.list(limit=5000)
        if not articles:
            return

        texts = [f"{article.topic} {article.content}" for article in articles]
        embeddings = await encode(texts)

        rows: builtins.list[tuple[int, bytes]] = []
        for article, embedding in zip(articles, embeddings, strict=True):
            try:
                cursor = await self.db.execute(
                    "SELECT rowid FROM knowledge WHERE id = ?",
                    (str(article.id),),
                )
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                logger.warning("Vec rebuild skipped knowledge %s", article.id, exc_info=True)
                continue

        async with self._vec_lock:
            await self.db.execute("DROP TABLE IF EXISTS knowledge_vec")
            await self.db.execute("CREATE VIRTUAL TABLE knowledge_vec USING vec0(embedding float[384])")
            for rowid, embedding in rows:
                await self.db.execute(
                    "INSERT INTO knowledge_vec(rowid, embedding) VALUES(?, ?)",
                    (rowid, embedding),
                )
            await self.db.commit()
