"""Story store — CRUD for tiered narrative arcs."""

from __future__ import annotations
from typing import List

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import aiosqlite

from charlieverse.models.story import Story, StoryTier

logger = logging.getLogger(__name__)


def _tags_json(tags: list[str] | None) -> str | None:
    return json.dumps(tags) if tags else None


def _tags_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parsed = json.loads(raw)
    return parsed if parsed else None


def _row_to_story(row: aiosqlite.Row) -> Story:
    return Story(
        id=UUID(row["id"]),
        title=row["title"],
        summary=row["summary"],
        content=row["content"],
        tier=StoryTier(row["tier"]),
        period_start=row["period_start"],
        period_end=row["period_end"],
        workspace=row["workspace"],
        session_id=UUID(row["session_id"]) if row["session_id"] else None,
        tags=_tags_list(row["tags"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class StoryStore:
    """Store for story arc operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db
        self._vec_lock = asyncio.Lock()

    async def create(self, story: Story) -> Story:
        """Insert a new story."""
        await self.db.execute(
            """INSERT INTO stories (id, title, summary, content, tier, period_start, period_end,
               workspace, session_id, tags, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(story.id),
                story.title,
                story.summary,
                story.content,
                story.tier.value,
                story.period_start,
                story.period_end,
                story.workspace,
                str(story.session_id) if story.session_id else None,
                _tags_json(story.tags),
                story.created_at.isoformat(),
                story.updated_at.isoformat(),
                story.deleted_at.isoformat() if story.deleted_at else None,
            ),
        )
        await self._sync_fts(story)
        await self._sync_vec(story)
        await self.db.commit()
        return story

    async def upsert(self, story: Story) -> Story:
        """Insert or update a story. For session stories, matches on session_id."""
        existing = None
        if story.session_id:
            existing = await self.find_by_session(story.session_id)
        if not existing:
            existing = await self.get(story.id)
        if existing:
            story.id = existing.id
            story.created_at = existing.created_at
            return await self.update(story)
        return await self.create(story)

    async def find_by_session(self, session_id: UUID) -> Story | None:
        """Find the session-tier story for a given session."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE session_id = ? AND deleted_at IS NULL LIMIT 1",
            (str(session_id),),
        )
        row = await cursor.fetchone()
        return _row_to_story(row) if row else None

    async def get(self, story_id: UUID) -> Story | None:
        """Fetch a story by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE id = ? AND deleted_at IS NULL LIMIT 1",
            (str(story_id),),
        )
        row = await cursor.fetchone()
        return _row_to_story(row) if row else None

    async def get_all_time(self) -> Story | None:
        """Fetch a story by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE tier = 'all-time' AND deleted_at IS NULL LIMIT 1"
        )
        row = await cursor.fetchone()
        return _row_to_story(row) if row else None

    async def list(
        self,
        tier: StoryTier | None = None,
        limit: int = 50,
    ) -> List[Story]:
        """List stories, optionally filtered by tier."""
        if tier:
            cursor = await self.db.execute(
                "SELECT * FROM stories WHERE tier = ? AND deleted_at IS NULL ORDER BY period_start DESC LIMIT ?",
                (tier.value, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM stories WHERE deleted_at IS NULL ORDER BY period_start DESC LIMIT ?",
                (limit,),
            )
        return [_row_to_story(row) for row in await cursor.fetchall()]

    async def find_by_period(
        self,
        start: str,
        end: str,
        limit: int = 5,
        workspace: str | None = None,
    ) -> List[Story]:
        """Find stories whose period overlaps with the given date range.

        Args:
            start: ISO date string for range start.
            end: ISO date string for range end.
            limit: Max results.
            workspace: If set, only return stories scoped to this workspace.
        """
        if workspace:
            cursor = await self.db.execute(
                """SELECT * FROM stories
                   WHERE deleted_at IS NULL
                   AND DATE(period_start, 'localtime') <= ? AND DATE(period_end, 'localtime') >= ?
                   AND (workspace = ? OR workspace IS NULL)
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (end, start, workspace, limit),
            )
        else:
            cursor = await self.db.execute(
                """SELECT * FROM stories
                   WHERE deleted_at IS NULL
                   AND DATE(period_start, 'localtime') <= ? AND DATE(period_end, 'localtime') >= ?
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (end, start, limit),
            )
        return [_row_to_story(row) for row in await cursor.fetchall()]

    async def update(self, story: Story) -> Story:
        """Update an existing story."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            """UPDATE stories SET title = ?, summary = ?, content = ?, tier = ?,
               period_start = ?, period_end = ?, workspace = ?, session_id = ?,
               tags = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL""",
            (
                story.title,
                story.summary,
                story.content,
                story.tier.value,
                story.period_start,
                story.period_end,
                story.workspace,
                str(story.session_id) if story.session_id else None,
                _tags_json(story.tags),
                now.isoformat(),
                str(story.id),
            ),
        )
        await self._sync_fts(story)
        await self._sync_vec(story)
        await self.db.commit()
        return story

    async def delete(self, story_id: UUID) -> None:
        """Soft-delete a story."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE stories SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now.isoformat(), now.isoformat(), str(story_id)),
        )
        await self.db.commit()

    # --- FTS ---

    async def _sync_fts(self, story: Story) -> None:
        """Sync a story to the FTS index."""
        cursor = await self.db.execute(
            "SELECT rowid FROM stories WHERE id = ?", (str(story.id),)
        )
        row = await cursor.fetchone()
        if not row:
            return
        rowid = row[0]
        await self.db.execute(
            "INSERT INTO stories_fts(stories_fts, rowid, title, summary, content, tags) VALUES('delete', ?, ?, ?, ?, ?)",
            (rowid, story.title, story.summary or "", story.content, _tags_json(story.tags) or ""),
        )
        await self.db.execute(
            "INSERT INTO stories_fts(rowid, title, summary, content, tags) VALUES(?, ?, ?, ?, ?)",
            (rowid, story.title, story.summary or "", story.content, _tags_json(story.tags) or ""),
        )

    async def search(
        self,
        query: str,
        period_start: str | None = None,
        period_end: str | None = None,
        limit: int = 5,
    ) -> List[Story]:
        """Search stories via FTS, optionally filtered by date range.

        If both query and date range are provided, results must match both.
        If only query, searches all stories. If only dates, falls back to find_by_period.
        """
        if not query and period_start and period_end:
            return await self.find_by_period(period_start, period_end, limit)

        if not query:
            return []

        from charlieverse.db.fts import sanitize_fts_query

        fts_query = sanitize_fts_query(query)
        if not fts_query:
            return []

        if period_start and period_end:
            cursor = await self.db.execute(
                """SELECT stories.*, stories_fts.rank
                   FROM stories_fts
                   JOIN stories ON stories.rowid = stories_fts.rowid
                   WHERE stories_fts MATCH ?
                   AND stories.period_start <= ? AND stories.period_end >= ?
                   AND stories.deleted_at IS NULL
                   ORDER BY stories_fts.rank
                   LIMIT ?""",
                (fts_query, period_end, period_start, limit),
            )
        else:
            cursor = await self.db.execute(
                """SELECT stories.*, stories_fts.rank
                   FROM stories_fts
                   JOIN stories ON stories.rowid = stories_fts.rowid
                   WHERE stories_fts MATCH ?
                   AND stories.deleted_at IS NULL
                   ORDER BY stories_fts.rank
                   LIMIT ?""",
                (fts_query, limit),
            )
        return [_row_to_story(row) for row in await cursor.fetchall()]

    async def search_by_vector(
        self,
        embedding: List[float],
        period_start: str | None = None,
        period_end: str | None = None,
        limit: int = 5,
    ) -> List[Story]:
        """Search stories by vector similarity, optionally filtered by date range."""
        from sqlite_vec import serialize_float32

        if period_start and period_end:
            # Get more candidates from vec, then filter by date in Python
            # (sqlite-vec doesn't support WHERE clauses on joined tables in MATCH)
            cursor = await self.db.execute(
                """SELECT stories.*, v.distance FROM stories_vec v
                   JOIN stories ON stories.rowid = v.rowid
                   WHERE v.embedding MATCH ?
                   AND v.k = ?
                   AND stories.deleted_at IS NULL
                   AND stories.period_start <= ? AND stories.period_end >= ?
                   ORDER BY v.distance
                   LIMIT ?""",
                (serialize_float32(embedding), limit * 3, period_end, period_start, limit),
            )
        else:
            cursor = await self.db.execute(
                """SELECT stories.*, v.distance FROM stories_vec v
                   JOIN stories ON stories.rowid = v.rowid
                   WHERE v.embedding MATCH ?
                   AND v.k = ?
                   AND stories.deleted_at IS NULL
                   ORDER BY v.distance
                   LIMIT ?""",
                (serialize_float32(embedding), limit, limit),
            )
        return [_row_to_story(row) for row in await cursor.fetchall()]

    async def _sync_vec(self, story: Story) -> None:
        """Sync a story's embedding to the vector index. Best-effort — never fails the caller."""
        try:
            from charlieverse.embeddings import encode_one
            from sqlite_vec import serialize_float32

            text = f"{story.title}\n{story.summary or ''}\n{story.content}"
            embedding = await encode_one(text)

            cursor = await self.db.execute(
                "SELECT rowid FROM stories WHERE id = ?", (str(story.id),)
            )
            row = await cursor.fetchone()
            if row:
                async with self._vec_lock:
                    await self.db.execute(
                        "DELETE FROM stories_vec WHERE rowid = ?", (row[0],)
                    )
                    await self.db.execute(
                        "INSERT INTO stories_vec(rowid, embedding) VALUES(?, ?)",
                        (row[0], serialize_float32(embedding)),
                    )
        except Exception:
            logger.warning("Vec sync failed for story %s", story.id, exc_info=True)

    async def rebuild_fts(self) -> None:
        """Rebuild the FTS index from scratch."""
        await self.db.execute("INSERT INTO stories_fts(stories_fts) VALUES('rebuild')")
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all story embeddings from scratch."""
        from charlieverse.embeddings import encode_one
        from sqlite_vec import serialize_float32

        all_stories = await self.list(limit=1000)

        rows: list[tuple[int, bytes]] = []
        for story in all_stories:
            try:
                text = f"{story.title}\n{story.summary or ''}\n{story.content}"
                embedding = await encode_one(text)
                cursor = await self.db.execute(
                    "SELECT rowid FROM stories WHERE id = ?", (str(story.id),)
                )
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                logger.warning("Vec rebuild skipped story %s", story.id, exc_info=True)
                continue

        async with self._vec_lock:
            await self.db.execute("DELETE FROM stories_vec")
            for rowid, embedding in rows:
                await self.db.execute(
                    "INSERT INTO stories_vec(rowid, embedding) VALUES(?, ?)",
                    (rowid, embedding),
                )
            await self.db.commit()
