"""Story store — CRUD for tiered narrative arcs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import aiosqlite

from charlieverse.models.story import Story, StoryTier


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
        content=row["content"],
        tier=StoryTier(row["tier"]),
        period_start=row["period_start"],
        period_end=row["period_end"],
        tags=_tags_list(row["tags"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
    )


class StoryStore:
    """Store for story arc operations."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, story: Story) -> Story:
        """Insert a new story."""
        await self.db.execute(
            """INSERT INTO stories (id, title, content, tier, period_start, period_end,
               tags, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(story.id),
                story.title,
                story.content,
                story.tier.value,
                story.period_start,
                story.period_end,
                _tags_json(story.tags),
                story.created_at.isoformat(),
                story.updated_at.isoformat(),
                story.deleted_at.isoformat() if story.deleted_at else None,
            ),
        )
        await self.db.commit()
        return story

    async def get(self, story_id: UUID) -> Story | None:
        """Fetch a story by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM stories WHERE id = ? AND deleted_at IS NULL",
            (str(story_id),),
        )
        row = await cursor.fetchone()
        return _row_to_story(row) if row else None

    async def list(
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
        return [_row_to_story(row) for row in await cursor.fetchall()]

    async def update(self, story: Story) -> Story:
        """Update an existing story."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            """UPDATE stories SET title = ?, content = ?, tier = ?,
               period_start = ?, period_end = ?, tags = ?, updated_at = ?
               WHERE id = ? AND deleted_at IS NULL""",
            (
                story.title,
                story.content,
                story.tier.value,
                story.period_start,
                story.period_end,
                _tags_json(story.tags),
                now.isoformat(),
                str(story.id),
            ),
        )
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
