"""REST endpoints for story CRUD and story-data generation."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.db.stores import SessionStore, StoryStore
from charlieverse.db.stores.context import StoreContext
from charlieverse.helpers.uuid import uuid_from_str
from charlieverse.models import Session, StoryTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BAD_UUID = JSONResponse({"error": "Invalid UUID format"}, status_code=400)


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def _serialize_story(story) -> dict:
    """Convert a Story model to a JSON-safe dict."""
    return {
        "id": str(story.id),
        "title": story.title,
        "summary": story.summary,
        "content": story.content,
        "tier": story.tier.value,
        "period_start": story.period_start,
        "period_end": story.period_end,
        "workspace": story.workspace,
        "session_id": str(story.session_id) if story.session_id else None,
        "tags": story.tags,
        "created_at": story.created_at.isoformat(),
        "updated_at": story.updated_at.isoformat(),
    }


def _serialize_session(session) -> dict:
    """Convert a Session model to a JSON-safe dict for story-data responses."""
    return {
        "id": str(session.id),
        "what_happened": session.what_happened,
        "for_next_session": session.for_next_session,
        "tags": session.tags,
        "workspace": session.workspace,
        "transcript_path": session.transcript_path,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_routes(mcp: FastMCP, rest_stores: StoreContext) -> None:
    """Register story REST endpoints on the given FastMCP instance."""

    @mcp.custom_route("/api/stories", methods=["GET"])
    async def api_list_stories(request: Request) -> JSONResponse:
        """List stories, optionally filtered by tier."""
        stories: StoryStore = rest_stores["stories"]
        tier_param = request.query_params.get("tier")
        limit = int(request.query_params.get("limit", "50"))

        tier = StoryTier(tier_param) if tier_param else None
        story_list = await stories.list(tier=tier, limit=limit)

        return JSONResponse({"stories": [_serialize_story(s) for s in story_list]})

    @mcp.custom_route("/api/stories/{id}", methods=["GET"])
    async def api_get_story(request: Request) -> JSONResponse:
        """Get a single story by ID."""
        stories: StoryStore = rest_stores["stories"]
        uid = uuid_from_str(request.path_params["id"])
        if not uid:
            return _BAD_UUID

        story = await stories.get(uid)
        if not story:
            return JSONResponse({"error": "Story not found"}, status_code=404)

        return JSONResponse(_serialize_story(story))

    @mcp.custom_route("/api/stories", methods=["PUT"])
    async def api_upsert_story(request: Request) -> JSONResponse:
        """Upsert a story. For session stories, matches on session_id."""
        from charlieverse.models.story import Story

        body = await request.json()
        story_store: StoryStore = rest_stores["stories"]

        session_id = uuid_from_str(body["session_id"]) if body.get("session_id") else None

        if session_id:
            sessions_store: SessionStore = rest_stores["sessions"]
            existing = await sessions_store.get(session_id)
            if not existing:
                await sessions_store.create(
                    Session(
                        id=session_id,
                        workspace=body.get("workspace"),
                    )
                )

        title = body.get("title", "")
        summary = body.get("summary")
        content = body.get("content", "")

        if isinstance(title, str) and title.strip().startswith("{"):
            try:
                parsed = json.loads(title)
                if isinstance(parsed, dict):
                    title = parsed.get("title", title)
                    summary = summary or parsed.get("summary")
                    content = content or parsed.get("content", content)
            except json.JSONDecodeError:
                pass

        if isinstance(content, str) and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "content" in parsed:
                    title = title or parsed.get("title", "")
                    summary = summary or parsed.get("summary")
                    content = parsed.get("content", content)
            except json.JSONDecodeError:
                pass

        if not title or not content or len(content.strip()) < 20:
            return JSONResponse(
                {"error": "Story must have a title and content (min 20 chars)"},
                status_code=400,
            )

        story = Story(
            title=title,
            summary=summary,
            content=content,
            tier=StoryTier(body.get("tier", "session")),
            period_start=body.get("period_start"),
            period_end=body.get("period_end"),
            workspace=body.get("workspace"),
            session_id=session_id,
            tags=body.get("tags"),
        )

        result = await story_store.upsert(story)

        return JSONResponse(_serialize_story(result))

    @mcp.custom_route("/api/stories/{id}", methods=["DELETE"])
    async def api_delete_story(request: Request) -> JSONResponse:
        """Delete a story."""
        story_store: StoryStore = rest_stores["stories"]
        uid = uuid_from_str(request.path_params["id"])
        if not uid:
            return _BAD_UUID

        story = await story_store.get(uid)
        if not story:
            return JSONResponse({"error": "Story not found"}, status_code=404)

        await story_store.delete(uid)
        return JSONResponse({"deleted": True})

    @mcp.custom_route("/api/stories/cleanup", methods=["POST"])
    async def api_cleanup_stories(request: Request) -> JSONResponse:
        """Delete all stories with empty or 'test' titles."""
        story_store: StoryStore = rest_stores["stories"]
        db = rest_stores["db"]

        cursor = await db.execute(
            """SELECT id FROM stories
               WHERE deleted_at IS NULL
               AND (title IS NULL OR title = '' OR LOWER(title) = 'test' OR LOWER(title) = 'test title'
                    OR LENGTH(TRIM(title)) < 5)"""
        )
        rows = await cursor.fetchall()
        deleted = 0

        for row in rows:
            uuid = uuid_from_str(row["id"])
            if uuid:
                await story_store.delete(uuid)
                deleted += 1

        return JSONResponse({"deleted": deleted})

    @mcp.custom_route("/api/story-data/{session_id}", methods=["GET"])
    async def api_story_data_session(request: Request) -> JSONResponse:
        """Get all data needed for the Storyteller to generate/update a session story.

        Returns: messages, existing story, recent memories/knowledge since last save.
        """
        raw_session_id = request.path_params["session_id"]
        uid = uuid_from_str(raw_session_id)
        if not uid:
            return _BAD_UUID
        session_id = raw_session_id
        db = rest_stores["db"]
        sessions_store: SessionStore = rest_stores["sessions"]
        story_store: StoryStore = rest_stores["stories"]

        session = await sessions_store.get(uid)
        session_data = {
            "id": session_id,
            "workspace": session.workspace if session else None,
            "transcript_path": session.transcript_path if session else None,
            "created_at": session.created_at.isoformat() if session else None,
        }

        existing_story = await story_store.find_by_session(uid)
        existing_story_data = _serialize_story(existing_story) if existing_story else None

        last_update = existing_story.updated_at.isoformat() if existing_story else None

        if last_update:
            cursor = await db.execute(
                """SELECT id, session_id, role, content, created_at
                   FROM messages
                   WHERE session_id = ? AND created_at > ?
                   ORDER BY created_at ASC""",
                (session_id, last_update),
            )
        else:
            cursor = await db.execute(
                """SELECT id, session_id, role, content, created_at
                   FROM messages
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,),
            )
        msg_rows = await cursor.fetchall()

        messages = []
        prev_time = None
        for row in msg_rows:
            created = datetime.fromisoformat(row["created_at"])
            seconds_between = None
            if prev_time:
                seconds_between = str(int((created - prev_time).total_seconds()))
            prev_time = created

            messages.append(
                {
                    "content": row["content"],
                    "from": "charlie" if row["role"] == "assistant" else "user",
                    "date_time": created.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                    "seconds_between_messages": seconds_between,
                }
            )

        cursor = await db.execute(
            """SELECT id, type, content, tags, created_at FROM entities
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (session_id,),
        )
        memory_rows = await cursor.fetchall()
        memories_data = [{"type": row["type"], "content": row["content"][:300], "tags": row["tags"]} for row in memory_rows]

        cursor = await db.execute(
            """SELECT id, topic, content, tags, created_at FROM knowledge
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (session_id,),
        )
        knowledge_rows = await cursor.fetchall()
        knowledge_data = [{"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]} for row in knowledge_rows]

        return JSONResponse(
            {
                "session": session_data,
                "existing_story": existing_story_data,
                "messages": messages,
                "memories": memories_data,
                "knowledge": knowledge_data,
            }
        )

    @mcp.custom_route("/api/story-data/{tier}/{date}", methods=["GET"])
    async def api_story_data_tier(request: Request) -> JSONResponse:
        """Get lower-tier stories for rollup generation.

        E.g., /api/story-data/weekly/2026-03-16 returns daily stories for that week.
        """
        tier = request.path_params["tier"]
        date_str = request.path_params["date"]
        story_store: StoryStore = rest_stores["stories"]

        target_date = date.fromisoformat(date_str)

        source_tier = None
        range_start = None
        range_end = None

        if tier == "daily":
            sessions_store: SessionStore = rest_stores["sessions"]
            db = rest_stores["db"]
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

            day_start = f"{target_date.isoformat()}T00:00:00"
            cursor = await db.execute(
                """SELECT type, content, tags FROM entities
                   WHERE deleted_at IS NULL AND created_at >= ?
                   ORDER BY created_at ASC""",
                (day_start,),
            )
            memories = [{"type": row["type"], "content": row["content"][:300], "tags": row["tags"]} for row in await cursor.fetchall()]

            cursor = await db.execute(
                """SELECT topic, content, tags FROM knowledge
                   WHERE deleted_at IS NULL AND created_at >= ?
                   ORDER BY created_at ASC""",
                (day_start,),
            )
            knowledge = [{"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]} for row in await cursor.fetchall()]

            return JSONResponse(
                {
                    "tier": "daily",
                    "date": date_str,
                    "range_start": target_date.isoformat(),
                    "range_end": target_date.isoformat(),
                    "sessions": [_serialize_session(s) for s in sessions],
                    "messages": messages,
                    "memories": memories,
                    "knowledge": knowledge,
                }
            )
        elif tier == "weekly":
            source_tier = StoryTier.daily
            monday = target_date - timedelta(days=target_date.weekday())
            sunday = monday + timedelta(days=6)
            range_start = monday.isoformat()
            range_end = sunday.isoformat()
        elif tier == "monthly":
            source_tier = StoryTier.weekly
            range_start = target_date.replace(day=1).isoformat()
            if target_date.month == 12:
                range_end = target_date.replace(year=target_date.year + 1, month=1, day=1).isoformat()
            else:
                range_end = target_date.replace(month=target_date.month + 1, day=1).isoformat()
        elif tier == "quarterly":
            source_tier = StoryTier.monthly
            quarter_start_month = ((target_date.month - 1) // 3) * 3 + 1
            range_start = target_date.replace(month=quarter_start_month, day=1).isoformat()
            end_month = quarter_start_month + 3
            if end_month > 12:
                range_end = target_date.replace(year=target_date.year + 1, month=end_month - 12, day=1).isoformat()
            else:
                range_end = target_date.replace(month=end_month, day=1).isoformat()
        elif tier == "yearly":
            source_tier = StoryTier.quarterly
            range_start = target_date.replace(month=1, day=1).isoformat()
            range_end = target_date.replace(year=target_date.year + 1, month=1, day=1).isoformat()
        else:
            return JSONResponse({"error": f"Unknown tier: {tier}"}, status_code=400)

        stories = await story_store.find_by_period(range_start, range_end, limit=50)
        if source_tier:
            stories = [s for s in stories if s.tier == source_tier]

        return JSONResponse(
            {
                "tier": tier,
                "date": date_str,
                "source_tier": source_tier.value if source_tier else None,
                "range_start": range_start,
                "range_end": range_end,
                "stories": [_serialize_story(s) for s in stories],
            }
        )

    @mcp.custom_route("/api/rebuild", methods=["POST"])
    async def api_rebuild(request: Request) -> JSONResponse:
        """Rebuild all FTS and vector indexes across entities, knowledge, and stories."""
        from charlieverse.db.stores.context import rebuild_all

        await rebuild_all(rest_stores)
        return JSONResponse({"success": True})
