"""Story store — CRUD, search, and aggregation for tiered narrative arcs."""

from __future__ import annotations

import asyncio
import logging

from aiosqlite import Connection

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import utc_now
from charlieverse.types.lists import encode_tag_list
from charlieverse.types.strings import WorkspaceFilePath

from .models import DeleteStory, NewStory, Story, StoryId, StoryTier, UpdateStory

logger = logging.getLogger(__name__)


class StoryError(Exception):
    """An error in the Story Store."""


class StoryStore:
    """Store for story arc operations. The only place stories are queried."""

    def __init__(self, db: Connection) -> None:
        self.db = db
        self._vec_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, story: NewStory) -> Story:
        """Insert a new story."""
        await self.db.execute(
            """INSERT INTO stories (id, title, summary, content, tier, period_start, period_end,
               workspace, session_id, tags, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                story.id,
                story.title,
                story.summary,
                story.content,
                story.tier.value,
                story.period_start,
                story.period_end,
                story.workspace,
                story.session_id if story.session_id else None,
                encode_tag_list(story.tags) if story.tags else None,
                story.created_at.isoformat(),
                story.created_at.isoformat(),
                None,
            ),
        )
        created = await self.get(story.id)
        if not created:
            raise StoryError("Could not fetch story after creating")
        await self._sync_fts_insert(created)
        await self._sync_vec(created)
        await self.db.commit()
        return created

    async def update(self, story: UpdateStory) -> Story:
        """Update an existing story."""
        await self._sync_fts_delete(story.id)
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
                story.session_id if story.session_id else None,
                encode_tag_list(story.tags) if story.tags else None,
                story.updated_at.isoformat(),
                story.id,
            ),
        )
        updated = await self.get(story.id)
        if not updated:
            raise StoryError("Could not fetch story after updating")

        await self._sync_fts_insert(updated)
        await self._sync_vec(updated)
        await self.db.commit()
        return updated

    async def upsert(self, story: NewStory) -> Story:
        """Insert or update a story.

        Match order:
        1. Session stories → find by session_id
        2. Rollup stories → find by (tier, period_start, period_end)
        3. Fallback → find by id
        """
        existing: Story | None = None
        if story.session_id:
            existing = await self.find_by_session(story.session_id)
        if not existing and story.period_start and story.period_end:
            existing = await self.find_by_tier_and_period(story.tier, story.period_start, story.period_end)
        if not existing:
            existing = await self.get(story.id)

        if existing:
            return await self.update(
                UpdateStory(
                    id=existing.id,
                    title=story.title,
                    summary=story.summary,
                    content=story.content,
                    tier=story.tier,
                    period_start=story.period_start,
                    period_end=story.period_end,
                    workspace=story.workspace,
                    session_id=story.session_id,
                    tags=story.tags,
                    updated_at=utc_now(),
                )
            )
        return await self.create(story)

    async def get(self, story_id: StoryId) -> Story | None:
        """Fetch a story by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE id = ? AND deleted_at IS NULL LIMIT 1",
            (story_id,),
        )
        row = await cursor.fetchone()
        return Story.from_row(row) if row else None

    async def get_all_time(self) -> Story | None:
        """Fetch the all-time story."""
        cursor = await self.db.execute("SELECT * FROM stories WHERE tier = 'all-time' AND deleted_at IS NULL LIMIT 1")
        row = await cursor.fetchone()
        return Story.from_row(row) if row else None

    async def find_by_session(self, session_id: SessionId) -> Story | None:
        """Find the session-tier story for a given session."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE session_id = ? AND deleted_at IS NULL LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        return Story.from_row(row) if row else None

    async def periods_by_tier(
        self,
        tier: StoryTier,
    ) -> list[tuple[str, str]]:
        """Return (period_start, period_end) pairs for all non-deleted stories at a tier."""
        cursor = await self.db.execute(
            "SELECT period_start, period_end FROM stories WHERE tier = ? AND deleted_at IS NULL",
            (tier.value,),
        )
        return [(row["period_start"], row["period_end"]) for row in await cursor.fetchall()]

    async def min_period_start(self, tier: StoryTier) -> str | None:
        """Earliest period_start across all non-deleted stories at a tier."""
        cursor = await self.db.execute(
            "SELECT MIN(period_start) FROM stories WHERE tier = ? AND deleted_at IS NULL",
            (tier.value,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def find_by_tier_and_period(
        self,
        tier: StoryTier,
        period_start: str,
        period_end: str,
    ) -> Story | None:
        """Find a rollup story matching tier and period window (tz-agnostic)."""
        cursor = await self.db.execute(
            """SELECT * FROM stories
               WHERE tier = ?
               AND SUBSTR(period_start, 1, 10) = SUBSTR(?, 1, 10)
               AND SUBSTR(period_end, 1, 10) = SUBSTR(?, 1, 10)
               AND deleted_at IS NULL
               LIMIT 1""",
            (tier.value, period_start, period_end),
        )
        row = await cursor.fetchone()
        return Story.from_row(row) if row else None

    async def fetch(
        self,
        tier: StoryTier | None = None,
        limit: int = 50,
    ) -> list[Story]:
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
        return [Story.from_row(row) for row in await cursor.fetchall()]

    async def find_by_period(
        self,
        start: str,
        end: str,
        tier: StoryTier | None = None,
        workspace: WorkspaceFilePath | None = None,
    ) -> list[Story]:
        fields: list[str | int] = [end, start]
        if tier:
            fields.append(tier)

        """Find stories whose period overlaps the given range."""
        cursor = await self.db.execute(
            f"""SELECT * FROM stories
               WHERE deleted_at IS NULL
               AND DATE(period_start, 'localtime') <= ? AND DATE(period_end, 'localtime') >= ?
               {"AND tier = ?" if tier else ""}
               ORDER BY updated_at DESC
               """,
            fields,
        )
        return [Story.from_row(row) for row in await cursor.fetchall()]

    async def delete(self, delete: DeleteStory) -> None:
        """Soft-delete a story."""
        await self.db.execute(
            "UPDATE stories SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
            (delete.deleted_at.isoformat(), delete.deleted_at.isoformat(), delete.id),
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        period_start: str | None = None,
        period_end: str | None = None,
        limit: int = 5,
    ) -> list[Story]:
        """FTS search with optional date range filter."""
        if not query and period_start and period_end:
            return await self.find_by_period(period_start, period_end)

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
        return [Story.from_row(row) for row in await cursor.fetchall()]

    async def search_by_vector(
        self,
        embedding: list[float],
        period_start: str | None = None,
        period_end: str | None = None,
        limit: int = 5,
    ) -> list[Story]:
        """Vector similarity search with optional date range filter."""
        from sqlite_vec import serialize_float32

        if period_start and period_end:
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
                (serialize_float32(embedding), limit * 3, limit),
            )
        return [Story.from_row(row) for row in await cursor.fetchall()]

    # ------------------------------------------------------------------
    # FTS + Vec sync (internal)
    # ------------------------------------------------------------------

    async def _sync_fts_insert(self, story: Story) -> None:
        cursor = await self.db.execute("SELECT rowid FROM stories WHERE id = ?", (story.id,))
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO stories_fts(rowid, title, summary, content, tags) VALUES(?, ?, ?, ?, ?)",
            (
                row[0],
                story.title,
                story.summary or "",
                story.content,
                encode_tag_list(story.tags) if story.tags else "",
            ),
        )

    async def _sync_fts_delete(self, story_id: StoryId) -> None:
        cursor = await self.db.execute(
            "SELECT rowid, title, summary, content, tags FROM stories WHERE id = ?",
            (story_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return
        await self.db.execute(
            "INSERT INTO stories_fts(stories_fts, rowid, title, summary, content, tags) VALUES('delete', ?, ?, ?, ?, ?)",
            (row[0], row[1], row[2] or "", row[3], row[4] or ""),
        )

    async def _sync_vec(self, story: Story) -> None:
        """Best-effort embedding sync. Never fails the caller."""
        try:
            from sqlite_vec import serialize_float32

            from charlieverse.embeddings import encode_one

            text = story.embed_content
            embedding = await encode_one(text)

            async with self._vec_lock:
                cursor = await self.db.execute("SELECT rowid FROM stories WHERE id = ?", (story.id,))
                row = await cursor.fetchone()
                if row:
                    await self.db.execute("DELETE FROM stories_vec WHERE rowid = ?", (row[0],))
                    await self.db.execute(
                        "INSERT INTO stories_vec(rowid, embedding) VALUES(?, ?)",
                        (row[0], serialize_float32(embedding)),
                    )
        except Exception:
            logger.warning("Vec sync failed for story %s", story.id, exc_info=True)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def rebuild(self) -> None:
        from asyncio import gather

        await gather(self.rebuild_fts(), self.rebuild_vec())

    async def rebuild_fts(self) -> None:
        await self.db.execute("INSERT INTO stories_fts(stories_fts) VALUES('rebuild')")
        await self.db.commit()

    async def rebuild_vec(self) -> None:
        """Rebuild all story embeddings from scratch."""
        from sqlite_vec import serialize_float32

        from charlieverse.embeddings import encode

        all_stories = await self.fetch(limit=1000)
        if not all_stories:
            return

        texts = [story.embed_content for story in all_stories]
        embeddings = await encode(texts)

        rows: list[tuple[int, bytes]] = []
        for story, embedding in zip(all_stories, embeddings, strict=True):
            try:
                cursor = await self.db.execute("SELECT rowid FROM stories WHERE id = ?", (story.id,))
                row = await cursor.fetchone()
                if row:
                    rows.append((row[0], serialize_float32(embedding)))
            except Exception:
                logger.warning("Vec rebuild skipped story %s", story.id, exc_info=True)
                continue

        async with self._vec_lock:
            await self.db.execute("DROP TABLE IF EXISTS stories_vec")
            await self.db.execute("CREATE VIRTUAL TABLE stories_vec USING vec0(embedding float[384])")
            for rowid, embedding in rows:
                await self.db.execute(
                    "INSERT INTO stories_vec(rowid, embedding) VALUES(?, ?)",
                    (rowid, embedding),
                )
            await self.db.commit()

    async def delete_stub_stories(self) -> int:
        """Soft-delete stories with empty, placeholder, or very short titles.
        Returns the number of rows deleted."""
        cursor = await self.db.execute(
            """SELECT id FROM stories
               WHERE deleted_at IS NULL
               AND (title IS NULL OR title = ''
                    OR LOWER(title) = 'test' OR LOWER(title) = 'test title'
                    OR LENGTH(TRIM(title)) < 5)"""
        )
        rows = await cursor.fetchall()
        deleted = 0
        for row in rows:
            await self.delete(DeleteStory(id=StoryId(row["id"])))
            deleted += 1
        return deleted

    async def dedupe(self) -> None:
        """Remove duplicate rollup stories, keeping the most recently updated."""
        cursor = await self.db.execute("""
            SELECT tier, period_start, period_end, COUNT(*) as cnt
            FROM stories
            WHERE deleted_at IS NULL AND session_id IS NULL
            GROUP BY tier, SUBSTR(period_start, 1, 10), SUBSTR(period_end, 1, 10)
            HAVING cnt > 1
        """)
        groups = list(await cursor.fetchall())
        if not groups:
            return

        deleted = 0
        for row in groups:
            tier, p_start, p_end = row[0], row[1], row[2]
            dupes = await self.db.execute(
                """SELECT id FROM stories
                WHERE tier = ? AND SUBSTR(period_start, 1, 10) = SUBSTR(?, 1, 10) AND SUBSTR(period_end, 1, 10) = SUBSTR(?, 1, 10)
                AND deleted_at IS NULL AND session_id IS NULL
                ORDER BY updated_at DESC""",
                (tier, p_start, p_end),
            )
            ids = [r[0] for r in await dupes.fetchall()]
            for stale_id in ids[1:]:
                await self.delete(DeleteStory(id=StoryId(stale_id)))
                deleted += 1

        if deleted:
            logger.info("Deduped %d rollup stories across %d groups", deleted, len(groups))
