"""Entity store — CRUD, search, and maintenance for memory entities.

This is the only place entities are queried.
"""

from __future__ import annotations

import asyncio
import builtins
import logging

import aiosqlite

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime, utc_now
from charlieverse.types.lists import encode_tag_list

from .models import DeleteEntity, Entity, EntityId, EntityType, NewEntity, UpdateEntity

logger = logging.getLogger(__name__)


class EntityError(Exception):
    """An error in the Entity Store."""


class EntityStore:
    """Store for entity (memory) operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db
        self._vec_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, entity: NewEntity) -> Entity:
        """Insert a new entity."""
        await self.db.execute(
            """INSERT INTO entities (id, type, content, tags, pinned, created_session_id,
               updated_session_id, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(entity.id),
                entity.type.value,
                entity.content,
                encode_tag_list(entity.tags) if entity.tags else None,
                int(entity.pinned),
                str(entity.created_session_id),
                None,
                entity.created_at.isoformat(),
                entity.created_at.isoformat(),
                None,
            ),
        )
        created = await self.get(entity.id)
        if not created:
            raise EntityError("Could not fetch entity after creating")
        await self._sync_fts_insert(created)
        await self.db.commit()
        return created

    async def update(self, update: UpdateEntity) -> Entity:
        """Update an existing entity. Only set fields are changed."""
        existing = await self.get(update.id)
        if not existing:
            raise EntityError(f"Entity {update.id!s} not found")

        merged_content = update.content if update.content is not None else existing.content
        merged_tags = update.tags if update.tags is not None else existing.tags
        merged_pinned = update.pinned if update.pinned is not None else existing.pinned
        merged_updated_session = update.updated_session_id if update.updated_session_id is not None else existing.updated_session_id

        await self._sync_fts_delete(update.id)
        cursor = await self.db.execute(
            """UPDATE entities SET content = ?, tags = ?, pinned = ?,
               updated_session_id = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL RETURNING *""",
            (
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
            raise EntityError("Could not fetch entity after updating")

        updated = Entity.from_row(row)
        await self._sync_fts_insert(updated)
        await self.db.commit()
        return updated

    async def get(self, entity_id: EntityId) -> Entity | None:
        """Fetch an entity by ID. Returns None if not found or soft-deleted."""
        cursor = await self.db.execute(
            "SELECT * FROM entities WHERE id = ? AND deleted_at IS NULL",
            (str(entity_id),),
        )
        row = await cursor.fetchone()
        return Entity.from_row(row) if row else None

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
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def pinned(self) -> builtins.list[Entity]:
        """Fetch all pinned, active entities."""
        cursor = await self.db.execute(
            "SELECT * FROM entities WHERE pinned = 1 AND deleted_at IS NULL ORDER BY created_at DESC",
        )
        return [Entity.from_row(row) for row in await cursor.fetchall()]

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
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def for_session(self, session_id: SessionId) -> builtins.list[Entity]:
        """Fetch active entities created within a single session."""
        cursor = await self.db.execute(
            """SELECT * FROM entities
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (str(session_id),),
        )
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def created_since(self, since: UTCDatetime) -> builtins.list[Entity]:
        """Fetch active entities created at or after the given timestamp."""
        cursor = await self.db.execute(
            """SELECT * FROM entities
               WHERE deleted_at IS NULL AND created_at >= ?
               ORDER BY created_at ASC""",
            (since.isoformat(),),
        )
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def delete(self, delete: DeleteEntity) -> None:
        """Soft-delete an entity."""
        await self.db.execute(
            "UPDATE entities SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (delete.deleted_at.isoformat(), delete.deleted_at.isoformat(), str(delete.id)),
        )
        await self.db.commit()

    async def pin(self, entity_id: EntityId, pinned: bool) -> None:
        """Set the pinned state of an entity."""
        now = utc_now()
        await self.db.execute(
            "UPDATE entities SET pinned = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (int(pinned), now.isoformat(), str(entity_id)),
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str, include_pinned: bool = True, limit: int = 10) -> builtins.list[Entity]:
        """Full-text search across entities using FTS5 + BM25 ranking."""
        from charlieverse.db.fts import sanitize_fts_query

        fts_query = sanitize_fts_query(query)
        if not fts_query:
            return []

        cursor = await self.db.execute(
            f"""SELECT e.* FROM entities e
               JOIN entities_fts fts ON e.rowid = fts.rowid
               WHERE entities_fts MATCH ?
               AND e.deleted_at IS NULL
               {"AND pinned = false" if not include_pinned else ""}
               ORDER BY RANK
               LIMIT ?""",
            (fts_query, limit),
        )
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def search_by_vector(
        self,
        embedding: builtins.list[float],
        limit: int = 10,
    ) -> builtins.list[Entity]:
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
        return [Entity.from_row(row) for row in await cursor.fetchall()]

    async def upsert_embedding(self, entity_id: EntityId, embedding: builtins.list[float]) -> None:
        """Store or update the embedding for an entity."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute("SELECT rowid FROM entities WHERE id = ?", (str(entity_id),))
        row = await cursor.fetchone()
        if not row:
            return

        rowid = row[0]
        async with self._vec_lock:
            await self.db.execute("DELETE FROM entities_vec WHERE rowid = ?", (rowid,))
            await self.db.execute(
                "INSERT INTO entities_vec(rowid, embedding) VALUES (?, ?)",
                (rowid, serialize_float32(embedding)),
            )
            await self.db.commit()

    # ------------------------------------------------------------------
    # FTS sync (internal)
    # ------------------------------------------------------------------

    async def _sync_fts_insert(self, entity: Entity) -> None:
        """Insert a new entity into the FTS index."""
        cursor = await self.db.execute(
            "SELECT rowid FROM entities WHERE id = ?",
            (str(entity.id),),
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO entities_fts(rowid, content, tags) VALUES(?, ?, ?)",
            (
                row[0],
                entity.content,
                encode_tag_list(entity.tags) if entity.tags else "",
            ),
        )

    async def _sync_fts_delete(self, entity_id: EntityId) -> None:
        """Remove an entity's current FTS entry using values from the content table."""
        cursor = await self.db.execute(
            "SELECT rowid, content, tags FROM entities WHERE id = ?",
            (str(entity_id),),
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO entities_fts(entities_fts, rowid, content, tags) VALUES('delete', ?, ?, ?)",
            (row[0], row[1], row[2] or ""),
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def count_by_type(self) -> dict[str, int]:
        """Return {entity_type: count} for all non-deleted entities."""
        cursor = await self.db.execute("SELECT type, COUNT(*) as count FROM entities WHERE deleted_at IS NULL GROUP BY type")
        rows = await cursor.fetchall()
        return {row["type"]: row["count"] for row in rows}

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

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

        rows: builtins.list[tuple[int, bytes]] = []
        for entity, embedding in zip(entities, embeddings, strict=True):
            try:
                cursor = await self.db.execute(
                    "SELECT rowid FROM entities WHERE id = ?",
                    (str(entity.id),),
                )
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                logger.warning("Vec rebuild skipped entity %s", entity.id, exc_info=True)
                continue

        async with self._vec_lock:
            await self.db.execute("DROP TABLE IF EXISTS entities_vec")
            await self.db.execute("CREATE VIRTUAL TABLE entities_vec USING vec0(embedding float[384])")
            for rowid, embedding in rows:
                await self.db.execute(
                    "INSERT INTO entities_vec(rowid, embedding) VALUES(?, ?)",
                    (rowid, embedding),
                )
            await self.db.commit()
