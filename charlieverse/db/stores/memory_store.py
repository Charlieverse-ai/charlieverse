"""Memory store — CRUD and search for entities."""

from __future__ import annotations

import builtins
from uuid import UUID

import aiosqlite

from charlieverse.db.stores._utils import _tags_json, _tags_list
from charlieverse.memory.sessions import SessionId
from charlieverse.models import Entity, EntityType
from charlieverse.types.dates import UTCDatetime, from_iso, from_iso_or_none, utc_now


def _row_to_entity(row: aiosqlite.Row) -> Entity:
    return Entity(
        id=UUID(row["id"]),
        type=EntityType(row["type"]),
        content=row["content"],
        tags=_tags_list(row["tags"]),
        pinned=bool(row["pinned"]),
        created_session_id=UUID(row["created_session_id"]),
        updated_session_id=UUID(row["updated_session_id"]) if row["updated_session_id"] else None,
        created_at=from_iso(row["created_at"]),
        updated_at=from_iso(row["updated_at"]),
        deleted_at=from_iso_or_none(row["deleted_at"]),
    )


class MemoryStore:
    """Store for entity (memory) operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _sync_fts_insert(self, entity: Entity) -> None:
        """Insert a new entity into the FTS index."""
        cursor = await self.db.execute("SELECT rowid FROM entities WHERE id = ?", (str(entity.id),))
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO entities_fts(rowid, content, tags) VALUES(?, ?, ?)",
            (row[0], entity.content, _tags_json(entity.tags) or ""),
        )

    async def _sync_fts_delete(self, entity_id: UUID) -> None:
        """Remove an entity's current FTS entry using values from the content table."""
        cursor = await self.db.execute("SELECT rowid, content, tags FROM entities WHERE id = ?", (str(entity_id),))
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO entities_fts(entities_fts, rowid, content, tags) VALUES('delete', ?, ?, ?)",
            (row[0], row[1], row[2] or ""),
        )

    async def rebuild(self) -> None:
        from asyncio import gather

        await gather(self.rebuild_fts(), self.rebuild_vec())

    async def rebuild_fts(self) -> None:
        """Full FTS rebuild — used on startup, not per-write."""
        await self.db.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all entity embeddings from scratch.

        Drops and recreates the vec table to avoid corruption from partial
        writes on the vec0 virtual table.
        """
        from sqlite_vec import serialize_float32

        from charlieverse.embeddings import encode, prepare_entity_text

        entities = await self.list(limit=5000)
        if not entities:
            return

        texts = [prepare_entity_text(entity.content, entity.tags) for entity in entities]
        embeddings = await encode(texts)

        rows: list[tuple[int, bytes]] = []
        for entity, embedding in zip(entities, embeddings, strict=True):
            try:
                cursor = await self.db.execute("SELECT rowid FROM entities WHERE id = ?", (str(entity.id),))
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                continue

        await self.db.execute("DROP TABLE IF EXISTS entities_vec")
        await self.db.execute("CREATE VIRTUAL TABLE entities_vec USING vec0(embedding float[384])")
        for rowid, embedding in rows:
            await self.db.execute(
                "INSERT INTO entities_vec(rowid, embedding) VALUES(?, ?)",
                (rowid, embedding),
            )
        await self.db.commit()

    async def create(self, entity: Entity) -> Entity:
        """Insert a new entity."""
        await self.db.execute(
            """INSERT INTO entities (id, type, content, tags, pinned, created_session_id,
               updated_session_id, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(entity.id),
                entity.type.value,
                entity.content,
                _tags_json(entity.tags),
                int(entity.pinned),
                str(entity.created_session_id),
                str(entity.updated_session_id) if entity.updated_session_id else None,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
                entity.deleted_at.isoformat() if entity.deleted_at else None,
            ),
        )
        await self._sync_fts_insert(entity)
        await self.db.commit()
        return entity

    async def get(self, entity_id: UUID) -> Entity | None:
        """Fetch an entity by ID. Returns None if not found or soft-deleted."""
        cursor = await self.db.execute(
            "SELECT * FROM entities WHERE id = ? AND deleted_at IS NULL",
            (str(entity_id),),
        )
        row = await cursor.fetchone()
        return _row_to_entity(row) if row else None

    async def list(
        self,
        entity_type: EntityType | None = None,
        limit: int = 50,
    ) -> builtins.list[Entity]:
        """List active entities, optionally filtered by type."""
        if entity_type:
            cursor = await self.db.execute(
                "SELECT * FROM entities WHERE type = ? AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT ?",
                (entity_type.value, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM entities WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def update(self, entity: Entity) -> Entity:
        """Update an existing entity."""
        now = utc_now()
        # Delete old FTS entry BEFORE updating (needs old values from content table)
        await self._sync_fts_delete(entity.id)
        await self.db.execute(
            """UPDATE entities SET content = ?, tags = ?, pinned = ?,
               updated_session_id = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL""",
            (
                entity.content,
                _tags_json(entity.tags),
                int(entity.pinned),
                str(entity.updated_session_id) if entity.updated_session_id else None,
                now.isoformat(),
                str(entity.id),
            ),
        )
        # Insert new FTS entry AFTER updating
        await self._sync_fts_insert(entity)
        await self.db.commit()
        return entity

    async def delete(self, entity_id: UUID) -> None:
        """Soft-delete an entity."""
        now = utc_now()
        await self.db.execute(
            "UPDATE entities SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(entity_id)),
        )
        await self.db.commit()

    async def pin(self, entity_id: UUID, pinned: bool) -> None:
        """Set the pinned state of an entity."""
        now = utc_now()
        await self.db.execute(
            "UPDATE entities SET pinned = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (int(pinned), now.isoformat(), str(entity_id)),
        )
        await self.db.commit()

    async def pinned(self) -> builtins.list[Entity]:
        """Fetch all pinned, active entities."""
        cursor = await self.db.execute(
            "SELECT * FROM entities WHERE pinned = 1 AND deleted_at IS NULL ORDER BY created_at DESC",
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def for_sessions(self, session_ids: builtins.list[SessionId]) -> builtins.list[Entity]:
        """Fetch active entities linked to the given sessions."""
        if not session_ids:
            return []
        placeholders = ",".join("?" * len(session_ids))
        cursor = await self.db.execute(
            f"""SELECT * FROM entities
                WHERE created_session_id IN ({placeholders})
                AND deleted_at IS NULL
                ORDER BY created_at DESC""",
            [str(sid) for sid in session_ids],
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def for_session(self, session_id: SessionId) -> builtins.list[Entity]:
        """Fetch active entities created within a single session."""
        cursor = await self.db.execute(
            """SELECT * FROM entities
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (str(session_id),),
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def created_since(self, since: UTCDatetime) -> builtins.list[Entity]:
        """Fetch active entities created at or after the given timestamp."""
        cursor = await self.db.execute(
            """SELECT * FROM entities
               WHERE deleted_at IS NULL AND created_at >= ?
               ORDER BY created_at ASC""",
            (since.isoformat(),),
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def search(self, query: str, limit: int = 10) -> builtins.list[Entity]:
        """Full-text search across entities using FTS5 + BM25 ranking."""
        from charlieverse.db.fts import sanitize_fts_query

        fts_query = sanitize_fts_query(query)
        if not fts_query:
            return []

        cursor = await self.db.execute(
            """SELECT e.* FROM entities e
               JOIN entities_fts fts ON e.rowid = fts.rowid
               WHERE entities_fts MATCH ?
               AND e.deleted_at IS NULL
               ORDER BY bm25(entities_fts)
               LIMIT ?""",
            (fts_query, limit),
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def search_by_vector(self, embedding: builtins.list[float], limit: int = 10) -> builtins.list[Entity]:
        """Semantic search using sqlite-vec cosine similarity."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute(
            """SELECT e.*, v.distance FROM entities e
               JOIN entities_vec v ON e.rowid = v.rowid
               WHERE v.embedding MATCH ?
               AND v.k = ?
               AND e.deleted_at IS NULL
               ORDER BY v.distance
               LIMIT ?""",
            (serialize_float32(embedding), limit, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_entity(row) for row in rows]

    async def upsert_embedding(self, entity_id: UUID, embedding: builtins.list[float]) -> None:
        """Store or update the embedding for an entity."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute("SELECT rowid FROM entities WHERE id = ?", (str(entity_id),))
        row = await cursor.fetchone()
        if not row:
            return

        rowid = row[0]
        await self.db.execute("DELETE FROM entities_vec WHERE rowid = ?", (rowid,))
        await self.db.execute(
            "INSERT INTO entities_vec(rowid, embedding) VALUES (?, ?)",
            (rowid, serialize_float32(embedding)),
        )
        await self.db.commit()
