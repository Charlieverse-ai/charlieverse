"""Memory store — CRUD and search for entities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID
from typing import List

import aiosqlite

from charlieverse.models import Entity, EntityType


def _tags_json(tags: list[str] | None) -> str | None:
    return json.dumps(tags) if tags else None


def _tags_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parsed = json.loads(raw)
    return parsed if parsed else None


def _row_to_entity(row: aiosqlite.Row) -> Entity:
    return Entity(
        id=UUID(row["id"]),
        type=EntityType(row["type"]),
        content=row["content"],
        tags=_tags_list(row["tags"]),
        pinned=bool(row["pinned"]),
        created_session_id=UUID(row["created_session_id"]),
        updated_session_id=UUID(row["updated_session_id"]) if row["updated_session_id"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class MemoryStore:
    """Store for entity (memory) operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _rebuild_fts(self) -> None:
        """Rebuild FTS index from source table."""
        await self.db.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")

    async def rebuild_fts(self) -> None:
        """Public FTS rebuild."""
        await self._rebuild_fts()
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all entity embeddings from scratch."""
        from charlieverse.embeddings import encode_one, prepare_entity_text

        entities = await self.list(limit=5000)
        for entity in entities:
            try:
                text = prepare_entity_text(entity.content, entity.tags)
                embedding = await encode_one(text)
                await self.upsert_embedding(entity.id, embedding)
            except Exception:
                continue

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
        await self._rebuild_fts()
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
    ) -> List[Entity]:
        """List active entities, optionally filtered by type."""
        if entity_type:
            cursor = await self.db.execute(
                "SELECT * FROM entities WHERE type = ? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT ?",
                (entity_type.value, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM entities WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def update(self, entity: Entity) -> Entity:
        """Update an existing entity."""
        now = datetime.now(timezone.utc)
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
        await self._rebuild_fts()
        await self.db.commit()
        return entity

    async def delete(self, entity_id: UUID) -> None:
        """Soft-delete an entity."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE entities SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(entity_id)),
        )
        await self.db.commit()

    async def pin(self, entity_id: UUID, pinned: bool) -> None:
        """Set the pinned state of an entity."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE entities SET pinned = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (int(pinned), now.isoformat(), str(entity_id)),
        )
        await self.db.commit()

    async def pinned(self) -> List[Entity]:
        """Fetch all pinned, active entities."""
        cursor = await self.db.execute(
            "SELECT * FROM entities WHERE pinned = 1 AND deleted_at IS NULL ORDER BY created_at DESC",
        )
        return [_row_to_entity(row) for row in await cursor.fetchall()]

    async def for_sessions(self, session_ids: List[UUID]) -> List[Entity]:
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

    async def search(self, query: str, limit: int = 10) -> List[Entity]:
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

    async def search_by_vector(self, embedding: List[float], limit: int = 10) -> List[Entity]:
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

    async def upsert_embedding(self, entity_id: UUID, embedding: List[float]) -> None:
        """Store or update the embedding for an entity."""
        from sqlite_vec import serialize_float32

        cursor = await self.db.execute(
            "SELECT rowid FROM entities WHERE id = ?", (str(entity_id),)
        )
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
