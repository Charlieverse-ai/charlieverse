"""REST endpoints for story CRUD and story-data generation.

All queries flow through stores — no raw SQL in this module.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.sessions import NewSession, SessionId
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.memory.stories import DeleteStory, NewStory, StoryId, StoryStore, StoryTier
from charlieverse.server.responses import (
    CreatedResponse,
    DailyRollupData,
    DailyRollupMessage,
    DeletedCountResponse,
    DeletedResponse,
    EmptyResponse,
    EntityStub,
    ExceptionResponse,
    KnowledgeStub,
    ModelListResponse,
    ModelResponse,
    NotFoundResponse,
    SessionSummary,
    TierRollupData,
)
from charlieverse.types.dates import UTCDatetime, at_utc_midnight, from_iso
from charlieverse.types.strings import WorkspaceFilePath


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register story REST endpoints on the given FastMCP instance."""

    # ------------------------------------------------------------------
    # Story CRUD
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/stories", methods=["GET"])
    async def api_list_stories(request: Request) -> ModelListResponse | ExceptionResponse:
        """List stories, optionally filtered by tier and/or period range.

        Query params:
        - tier: story tier (session, daily, weekly, monthly, yearly, all-time)
        - period_start / period_end: inclusive date range (YYYY-MM-DD).
          When both are provided, stories whose period overlaps the range are
          returned via StoryStore.find_by_period (timezone-aware matching).
        - limit: cap on results when no period range is specified (default 50).
        """
        try:
            stories: StoryStore = rest_stores.stories
            tier_param = request.query_params.get("tier")
            period_start = request.query_params.get("period_start")
            period_end = request.query_params.get("period_end")
            limit = int(request.query_params.get("limit", "50"))

            tier = StoryTier(tier_param) if tier_param else None

            if period_start and period_end:
                story_list = await stories.find_by_period(period_start, period_end, tier=tier)
            else:
                story_list = await stories.fetch(tier=tier, limit=limit)
            return ModelListResponse(story_list)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/stories/{id}", methods=["GET"])
    async def api_get_story(request: Request) -> ModelResponse | NotFoundResponse | ExceptionResponse:
        """Get a single story by ID."""
        try:
            stories: StoryStore = rest_stores.stories
            story_id = StoryId(request.path_params["id"])

            story = await stories.get(story_id)
            if not story:
                return NotFoundResponse("Story")

            return ModelResponse(story)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/stories", methods=["PUT"])
    async def api_upsert_story(request: Request) -> CreatedResponse | ExceptionResponse:
        """Upsert a story. For session stories, matches on session_id."""
        try:
            body = await request.json()
            story_store: StoryStore = rest_stores.stories

            session_id = SessionId(body["session_id"]) if body.get("session_id") else None
            workspace = WorkspaceFilePath(body.get("workspace"))

            if session_id:
                sessions_store: SessionStore = rest_stores.sessions
                existing = await sessions_store.get(session_id)
                if not existing:
                    await sessions_store.create(
                        NewSession(
                            id=session_id,
                            workspace=workspace,
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
                raise ValueError("Story must have a title and content (min 20 chars)")

            new_story = NewStory(
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

            result = await story_store.upsert(new_story)
            return CreatedResponse(result)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/stories/{id}", methods=["DELETE"])
    async def api_delete_story(request: Request) -> DeletedResponse | NotFoundResponse | ExceptionResponse:
        """Delete a story."""
        try:
            story_store: StoryStore = rest_stores.stories
            story_id = StoryId(request.path_params["id"])

            story = await story_store.get(story_id)
            if not story:
                return NotFoundResponse("Story")

            await story_store.delete(DeleteStory(id=story_id))
            return DeletedResponse()
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/stories/cleanup", methods=["POST"])
    async def api_cleanup_stories(request: Request) -> DeletedCountResponse | ExceptionResponse:
        """Delete all stories with empty or stub titles."""
        try:
            story_store: StoryStore = rest_stores.stories
            deleted = await story_store.delete_stub_stories()
            return DeletedCountResponse(deleted)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/story-data/{tier}/{date}", methods=["GET"])
    async def api_story_data_tier(request: Request) -> ModelResponse | ExceptionResponse | EmptyResponse:
        """Get lower-tier stories (or raw data for daily) for rollup generation."""
        try:
            tier = StoryTier(request.path_params["tier"])
            date_str = request.path_params["date"]
            story_store: StoryStore = rest_stores.stories

            target_date = from_iso(date_str)

            range_start: str | None = None
            range_end: str | None = None
            range_tier: StoryTier = StoryTier.daily

            match tier:
                case StoryTier.daily:
                    return ModelResponse(await _daily_rollup_data(rest_stores, target_date))
                case StoryTier.weekly:
                    range_tier = StoryTier.daily
                    monday = target_date - timedelta(days=target_date.weekday())
                    sunday = monday + timedelta(days=6)
                    range_start = monday.isoformat()
                    range_end = sunday.isoformat()
                case StoryTier.monthly:
                    range_tier = StoryTier.weekly
                    range_start = target_date.replace(day=1).isoformat()
                    if target_date.month == 12:
                        range_end = target_date.replace(year=target_date.year + 1, month=1, day=1).isoformat()
                    else:
                        range_end = target_date.replace(month=target_date.month + 1, day=1).isoformat()

                case StoryTier.yearly:
                    range_tier = StoryTier.monthly
                    range_start = at_utc_midnight(date(target_date.year, 1, 1)).isoformat()
                    range_end = at_utc_midnight(date(target_date.year + 1, 1, 1)).isoformat()

                case StoryTier.all_time:
                    range_tier = StoryTier.monthly
                    range_start = target_date.min.isoformat()
                    range_start = target_date.max.isoformat()

            if not range_start or not range_end:
                return EmptyResponse()

            stories_in_range = await story_store.find_by_period(range_start, range_end, tier=range_tier)

            tier_payload = TierRollupData(
                date=date_str,
                range_start=range_start,
                range_end=range_end,
                stories=stories_in_range,
            )
            return ModelResponse(tier_payload)
        except Exception as e:
            return ExceptionResponse(e)


async def _daily_rollup_data(stores: Stores, today: UTCDatetime) -> DailyRollupData:
    """Build the daily story-data payload — sessions + messages + memories + knowledge."""
    sessions_store = stores.sessions
    memories_store = stores.memories
    knowledge_store = stores.knowledge

    today_start = at_utc_midnight(today)
    sessions = await sessions_store.recent_within_days(days=1)

    messages = await stores.messages.messages_since(today_start) or []
    entities = await memories_store.created_since(today_start)
    knowledge = await knowledge_store.created_since(today_start)

    return DailyRollupData(
        range_start=today_start.isoformat(),
        range_end=today_start.isoformat(),
        sessions=[
            SessionSummary(
                id=s.id,
                what_happened=s.what_happened,
                workspace=s.workspace,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in sessions
        ],
        messages=[DailyRollupMessage(role=m.role, content=m.content[:500], created_at=m.created_at) for m in messages],
        memories=[EntityStub(type=e.type.value, content=(e.content or "")[:300]) for e in entities],
        knowledge=[KnowledgeStub(topic=k.topic, content=(k.content or "")[:300]) for k in knowledge],
    )
