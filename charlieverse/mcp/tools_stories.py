"""MCP tools: upsert_story, list_stories, get_story, delete_story, get_story_data."""

from __future__ import annotations

from datetime import date, timedelta
from datetime import datetime as dt
from uuid import UUID

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.db.stores import SessionStore, StoryStore
from charlieverse.mcp.context import _permalink, _stores
from charlieverse.models import Session, StoryTier


def register(mcp: FastMCP) -> None:
    """Register all story MCP tools on the given FastMCP instance."""

    @mcp.tool
    async def upsert_story(
        title: str,
        content: str,
        tier: str,
        period_start: str,
        period_end: str,
        summary: str | None = None,
        session_id: str | None = None,
        workspace: str | None = None,
        tags: list[str] | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Create or update a story. For session stories, matches on session_id."""
        if not title.strip():
            raise ToolError("title cannot be empty")
        if not content.strip():
            raise ToolError("content cannot be empty")
        if not tier.strip():
            raise ToolError("tier cannot be empty")
        from charlieverse.models.story import Story

        stores = _stores(ctx)
        story_store: StoryStore = stores["stories"]
        sessions_store: SessionStore = stores["sessions"]

        sid = UUID(session_id) if session_id else None

        if sid:
            existing = await sessions_store.get(sid)
            if not existing:
                await sessions_store.create(Session(id=sid, workspace=workspace))

        story = Story(
            title=title,
            summary=summary,
            content=content,
            tier=StoryTier(tier),
            period_start=period_start,
            period_end=period_end,
            workspace=workspace,
            session_id=sid,
            tags=tags,
        )

        result = await story_store.upsert(story)

        return {
            "id": str(result.id),
            "title": result.title,
            "tier": result.tier.value,
            "url": _permalink("stories", str(result.id)),
        }

    @mcp.tool
    async def list_stories(
        tier: str | None = None,
        limit: int = 20,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """List stories, optionally filtered by tier (session, daily, weekly, monthly, all-time)."""
        stores = _stores(ctx)
        story_store: StoryStore = stores["stories"]

        story_tier = StoryTier(tier) if tier else None
        stories = await story_store.list(tier=story_tier, limit=limit)

        return {
            "stories": [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "tier": s.tier.value,
                    "period_start": s.period_start,
                    "period_end": s.period_end,
                    "summary": s.summary,
                }
                for s in stories
            ]
        }

    @mcp.tool
    async def get_story(
        id: str,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Get a story by ID. Returns full content."""
        if not id.strip():
            raise ToolError("id cannot be empty")
        stores = _stores(ctx)
        story_store: StoryStore = stores["stories"]

        story = await story_store.get(UUID(id))
        if not story:
            raise ToolError(f"Story {id!r} not found")

        return {
            "id": str(story.id),
            "title": story.title,
            "summary": story.summary,
            "content": story.content,
            "tier": story.tier.value,
            "period_start": story.period_start,
            "period_end": story.period_end,
            "session_id": str(story.session_id) if story.session_id else None,
            "workspace": story.workspace,
        }

    @mcp.tool
    async def delete_story(
        id: str,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Soft-delete a story."""
        if not id.strip():
            raise ToolError("id cannot be empty")
        stores = _stores(ctx)
        story_store: StoryStore = stores["stories"]

        story = await story_store.get(UUID(id))
        if not story:
            raise ToolError(f"Story {id!r} not found")

        await story_store.delete(UUID(id))
        return {"deleted": True, "id": id}

    @mcp.tool
    async def get_story_data(
        target: str,
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Get data for the Storyteller to generate a story.

        Args:
            target: Either a session_id (UUID) for session stories,
                    or a tier name (daily, weekly, monthly) for rollups.
                    Rollups return lower-tier stories for synthesis.
        """
        if not target.strip():
            raise ToolError("target cannot be empty")
        stores = _stores(ctx)
        story_store: StoryStore = stores["stories"]
        db = stores["db"]

        tier_names = {"daily", "weekly", "monthly", "quarterly", "yearly"}
        if target in tier_names:
            today = date.today()

            if target == "daily":
                sessions_store: SessionStore = stores["sessions"]
                sessions = await sessions_store.recent_within_days(days=1)
                session_ids = [str(s.id) for s in sessions]

                messages = []
                for sid in session_ids:
                    cursor = await db.execute(
                        """SELECT role, content, created_at FROM messages
                           WHERE session_id = ? ORDER BY created_at ASC""",
                        (sid,),
                    )
                    for row in await cursor.fetchall():
                        messages.append(
                            {
                                "from": "charlie" if row["role"] == "assistant" else "user",
                                "content": row["content"][:500],
                                "created_at": row["created_at"],
                            }
                        )

                today_start = f"{today.isoformat()}T00:00:00"
                cursor = await db.execute(
                    """SELECT type, content, tags FROM entities
                       WHERE deleted_at IS NULL AND created_at >= ?
                       ORDER BY created_at ASC""",
                    (today_start,),
                )
                memories = [{"type": row["type"], "content": row["content"][:300], "tags": row["tags"]} for row in await cursor.fetchall()]

                cursor = await db.execute(
                    """SELECT topic, content, tags FROM knowledge
                       WHERE deleted_at IS NULL AND created_at >= ?
                       ORDER BY created_at ASC""",
                    (today_start,),
                )
                knowledge = [{"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]} for row in await cursor.fetchall()]

                return {
                    "type": "rollup",
                    "tier": "daily",
                    "range_start": today.isoformat(),
                    "range_end": today.isoformat(),
                    "sessions": [
                        {
                            "id": str(s.id),
                            "what_happened": s.what_happened,
                            "for_next_session": s.for_next_session,
                            "workspace": s.workspace,
                            "tags": s.tags,
                            "created_at": s.created_at.isoformat(),
                        }
                        for s in sessions
                    ],
                    "messages": messages,
                    "memories": memories,
                    "knowledge": knowledge,
                }

            source_tier = None
            range_start = None
            range_end = None

            if target == "weekly":
                source_tier = StoryTier.daily
                monday = today - timedelta(days=today.weekday())
                sunday = monday + timedelta(days=6)
                range_start = monday.isoformat()
                range_end = sunday.isoformat()
            elif target == "monthly":
                source_tier = StoryTier.weekly
                range_start = today.replace(day=1).isoformat()
                if today.month == 12:
                    range_end = today.replace(year=today.year + 1, month=1, day=1).isoformat()
                else:
                    range_end = today.replace(month=today.month + 1, day=1).isoformat()

            stories = await story_store.find_by_period(range_start or "", range_end or "", limit=50)
            if source_tier:
                stories = [s for s in stories if s.tier == source_tier]

            result: dict = {
                "type": "rollup",
                "tier": target,
                "range_start": range_start,
                "range_end": range_end,
                "stories": [
                    {
                        "id": str(s.id),
                        "title": s.title,
                        "summary": s.summary,
                        "content": s.content,
                        "tier": s.tier.value,
                        "period_start": s.period_start,
                        "period_end": s.period_end,
                    }
                    for s in stories
                ],
            }

            # Fallback: if no lower-tier stories exist for the period,
            # provide raw sessions so the Storyteller can still generate
            # the rollup without requiring every intermediate tier.
            if not stories and range_start and range_end:
                sessions_store = stores["sessions"]
                sessions = await sessions_store.recent_within_range(
                    range_start,
                    range_end,
                )
                if sessions:
                    result["fallback"] = "sessions"
                    result["sessions"] = [
                        {
                            "id": str(s.id),
                            "what_happened": s.what_happened,
                            "for_next_session": s.for_next_session,
                            "workspace": s.workspace,
                            "tags": s.tags,
                            "created_at": s.created_at.isoformat(),
                        }
                        for s in sessions
                    ]

            return result
        else:
            session_id = target
            sessions_store: SessionStore = stores["sessions"]

            session = await sessions_store.get(UUID(session_id))
            existing_story = await story_store.find_by_session(UUID(session_id))
            last_update = existing_story.updated_at.isoformat() if existing_story else None

            if last_update:
                cursor = await db.execute(
                    """SELECT id, role, content, created_at FROM messages
                       WHERE session_id = ? AND created_at > ?
                       ORDER BY created_at ASC""",
                    (session_id, last_update),
                )
            else:
                cursor = await db.execute(
                    """SELECT id, role, content, created_at FROM messages
                       WHERE session_id = ? ORDER BY created_at ASC""",
                    (session_id,),
                )
            msg_rows = await cursor.fetchall()

            messages = []
            prev_time = None
            for row in msg_rows:
                created = dt.fromisoformat(row["created_at"])
                seconds_between = None
                if prev_time:
                    seconds_between = str(int((created - prev_time).total_seconds()))
                prev_time = created
                messages.append(
                    {
                        "content": row["content"],
                        "from": "charlie" if row["role"] == "assistant" else "user",
                        "date_time": created.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                        "seconds_between": seconds_between,
                    }
                )

            cursor = await db.execute(
                """SELECT type, content, tags FROM entities
                   WHERE created_session_id = ? AND deleted_at IS NULL
                   ORDER BY created_at ASC""",
                (session_id,),
            )
            memories = [{"type": row["type"], "content": row["content"][:300], "tags": row["tags"]} for row in await cursor.fetchall()]

            return {
                "type": "session",
                "session_id": session_id,
                "workspace": session.workspace if session else None,
                "existing_story": {
                    "title": existing_story.title,
                    "summary": existing_story.summary,
                    "content": existing_story.content,
                }
                if existing_story
                else None,
                "messages": messages,
                "memories": memories,
            }
