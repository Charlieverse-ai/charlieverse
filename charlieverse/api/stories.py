"""REST endpoints for story CRUD and story-data generation.

All queries flow through stores — no raw SQL in this module.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.helpers.uuid import uuid_from_str
from charlieverse.memory.context import StoreContext
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.sessions import NewSession, Session, SessionId
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stories import DeleteStory, NewStory, Story, StoryId, StoryStore, StoryTier
from charlieverse.types.dates import UTCDatetime, at_utc_midnight, to_local

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BAD_UUID = JSONResponse({"error": "Invalid UUID format"}, status_code=400)


def _serialize_story(story: Story) -> dict[str, Any]:
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


def _serialize_session(session: Session) -> dict[str, Any]:
    """Convert a Session model to a JSON-safe dict for story-data responses."""
    return {
        "id": str(session.id),
        "what_happened": session.what_happened,
        "for_next_session": session.for_next_session,
        "tags": session.tags,
        "workspace": session.workspace,
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

        story = await stories.get(StoryId(uid))
        if not story:
            return JSONResponse({"error": "Story not found"}, status_code=404)

        return JSONResponse(_serialize_story(story))

    @mcp.custom_route("/api/stories", methods=["PUT"])
    async def api_upsert_story(request: Request) -> JSONResponse:
        """Upsert a story. For session stories, matches on session_id."""
        body = await request.json()
        story_store: StoryStore = rest_stores["stories"]

        session_uuid = uuid_from_str(body["session_id"]) if body.get("session_id") else None
        session_id = SessionId(session_uuid) if session_uuid else None

        if session_id:
            sessions_store: SessionStore = rest_stores["sessions"]
            existing = await sessions_store.get(session_id)
            if not existing:
                await sessions_store.create(
                    NewSession(
                        id=session_id,
                        workspace=body.get("workspace") or "unknown",
                    )
                )

        title = body.get("title", "")
        summary = body.get("summary")
        content = body.get("content", "")

        # Tolerate legacy callers that stuffed JSON into title/content.
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

        story = NewStory(
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

        story_id = StoryId(uid)
        story = await story_store.get(story_id)
        if not story:
            return JSONResponse({"error": "Story not found"}, status_code=404)

        await story_store.delete(DeleteStory(id=story_id))
        return JSONResponse({"deleted": True})

    @mcp.custom_route("/api/stories/cleanup", methods=["POST"])
    async def api_cleanup_stories(request: Request) -> JSONResponse:
        """Delete all stories with empty or stub titles."""
        story_store: StoryStore = rest_stores["stories"]
        deleted = await story_store.delete_stub_stories()
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
        session_id = SessionId(uid)

        sessions_store: SessionStore = rest_stores["sessions"]
        story_store: StoryStore = rest_stores["stories"]
        memories_store: EntityStore = rest_stores["memories"]
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]

        session = await sessions_store.get(session_id)
        session_data = {
            "id": raw_session_id,
            "workspace": session.workspace if session else None,
            "created_at": session.created_at.isoformat() if session else None,
        }

        existing_story = await story_store.find_by_session(session_id)
        existing_story_data = _serialize_story(existing_story) if existing_story else None
        since = existing_story.updated_at if existing_story else None

        session_messages = await sessions_store.messages_for_session(session_id, since=since)

        messages: list[dict[str, Any]] = []
        prev_time: UTCDatetime | None = None
        for msg in session_messages:
            seconds_between = None
            if prev_time is not None:
                seconds_between = str(int((msg.created_at - prev_time).total_seconds()))
            prev_time = msg.created_at
            messages.append(
                {
                    "content": msg.content,
                    "from": "charlie" if msg.role == "assistant" else "user",
                    "date_time": to_local(msg.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                    "seconds_between_messages": seconds_between,
                }
            )

        entities = await memories_store.for_session(session_id)
        knowledge = await knowledge_store.for_session(session_id)

        return JSONResponse(
            {
                "session": session_data,
                "existing_story": existing_story_data,
                "messages": messages,
                "memories": [{"type": e.type.value, "content": (e.content or "")[:300], "tags": e.tags} for e in entities],
                "knowledge": [{"topic": k.topic, "content": (k.content or "")[:300], "tags": k.tags} for k in knowledge],
            }
        )

    @mcp.custom_route("/api/story-data/{tier}/{date}", methods=["GET"])
    async def api_story_data_tier(request: Request) -> JSONResponse:
        """Get lower-tier stories (or raw data for daily) for rollup generation."""
        tier = request.path_params["tier"]
        date_str = request.path_params["date"]
        story_store: StoryStore = rest_stores["stories"]
        sessions_store: SessionStore = rest_stores["sessions"]
        memories_store: EntityStore = rest_stores["memories"]
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]

        target_date = date.fromisoformat(date_str)

        if tier == "daily":
            sessions = await sessions_store.recent_within_days(days=1)

            messages: list[dict[str, Any]] = []
            for s in sessions:
                session_messages = await sessions_store.messages_for_session(s.id)
                for msg in session_messages:
                    messages.append(
                        {
                            "from": "charlie" if msg.role == "assistant" else "user",
                            "content": (msg.content or "")[:500],
                            "created_at": msg.created_at.isoformat(),
                        }
                    )

            day_start = at_utc_midnight(target_date)
            entities = await memories_store.created_since(day_start)
            knowledge = await knowledge_store.created_since(day_start)

            return JSONResponse(
                {
                    "tier": "daily",
                    "date": date_str,
                    "range_start": target_date.isoformat(),
                    "range_end": target_date.isoformat(),
                    "sessions": [_serialize_session(s) for s in sessions],
                    "messages": messages,
                    "memories": [{"type": e.type.value, "content": (e.content or "")[:300], "tags": e.tags} for e in entities],
                    "knowledge": [{"topic": k.topic, "content": (k.content or "")[:300], "tags": k.tags} for k in knowledge],
                }
            )

        source_tier: StoryTier | None = None
        range_start: str | None = None
        range_end: str | None = None

        if tier == "weekly":
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

        stories = await story_store.find_by_period(range_start or "", range_end or "", limit=50)
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
