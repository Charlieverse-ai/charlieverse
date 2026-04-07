"""REST endpoints for story CRUD and story-data generation.

All queries flow through stores — no raw SQL in this module.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
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
    EntityStub,
    ExceptionResponse,
    KnowledgeStub,
    ModelListResponse,
    ModelResponse,
    NotFoundResponse,
    SessionStoryData,
    SessionStoryMessage,
    SessionStub,
    SessionSummary,
    TierRollupData,
)
from charlieverse.types.dates import UTCDatetime, at_utc_midnight, to_local


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register story REST endpoints on the given FastMCP instance."""

    # ------------------------------------------------------------------
    # Story CRUD
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/stories", methods=["GET"])
    async def api_list_stories(request: Request) -> ModelListResponse | ExceptionResponse:
        """List stories, optionally filtered by tier."""
        try:
            stories: StoryStore = rest_stores.stories
            tier_param = request.query_params.get("tier")
            limit = int(request.query_params.get("limit", "50"))

            tier = StoryTier(tier_param) if tier_param else None
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

            if session_id:
                sessions_store: SessionStore = rest_stores.sessions
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

    # ------------------------------------------------------------------
    # Story-data (Storyteller payloads)
    # ------------------------------------------------------------------

    @mcp.custom_route("/api/story-data/{session_id}", methods=["GET"])
    async def api_story_data_session(request: Request) -> ModelResponse | ExceptionResponse:
        """Get all data needed for the Storyteller to generate/update a session story.

        Returns: messages, existing story, recent memories/knowledge since last save.
        """
        try:
            session_id = SessionId(request.path_params["session_id"])

            sessions_store: SessionStore = rest_stores.sessions
            story_store: StoryStore = rest_stores.stories
            memories_store: EntityStore = rest_stores.memories
            knowledge_store: KnowledgeStore = rest_stores.knowledge

            session = await sessions_store.get(session_id)
            session_stub = SessionStub(
                id=session_id,
                workspace=session.workspace if session else None,
                created_at=session.created_at.isoformat() if session else None,
            )

            existing_story = await story_store.find_by_session(session_id)
            since = existing_story.updated_at if existing_story else None

            session_messages = await rest_stores.messages.messages_for_session(session_id, since=since)

            messages: list[SessionStoryMessage] = []
            prev_time: UTCDatetime | None = None
            for msg in session_messages:
                seconds_between = None
                if prev_time is not None:
                    seconds_between = str(int((msg.created_at - prev_time).total_seconds()))
                prev_time = msg.created_at
                messages.append(
                    SessionStoryMessage(
                        content=msg.content,
                        from_="charlie" if msg.role == "assistant" else "user",
                        date_time=to_local(msg.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                        seconds_between_messages=seconds_between,
                    )
                )

            entities = await memories_store.for_session(session_id)
            knowledge = await knowledge_store.for_session(session_id)

            payload = SessionStoryData(
                session=session_stub,
                existing_story=existing_story,
                messages=messages,
                memories=[EntityStub(type=e.type.value, content=(e.content or "")[:300], tags=e.tags) for e in entities],
                knowledge=[KnowledgeStub(topic=k.topic, content=(k.content or "")[:300], tags=k.tags) for k in knowledge],
            )
            return ModelResponse(payload)
        except Exception as e:
            return ExceptionResponse(e)

    @mcp.custom_route("/api/story-data/{tier}/{date}", methods=["GET"])
    async def api_story_data_tier(request: Request) -> ModelResponse | ExceptionResponse:
        """Get lower-tier stories (or raw data for daily) for rollup generation."""
        try:
            tier = request.path_params["tier"]
            date_str = request.path_params["date"]
            story_store: StoryStore = rest_stores.stories
            sessions_store: SessionStore = rest_stores.sessions
            memories_store: EntityStore = rest_stores.memories
            knowledge_store: KnowledgeStore = rest_stores.knowledge

            target_date = date.fromisoformat(date_str)

            if tier == "daily":
                sessions = await sessions_store.recent_within_days(days=1)

                messages: list[DailyRollupMessage] = []
                for s in sessions:
                    session_messages = await rest_stores.messages.messages_for_session(s.id)
                    for msg in session_messages:
                        messages.append(
                            DailyRollupMessage(
                                from_="charlie" if msg.role == "assistant" else "user",
                                content=(msg.content or "")[:500],
                                created_at=msg.created_at.isoformat(),
                            )
                        )

                day_start = at_utc_midnight(target_date)
                entities = await memories_store.created_since(day_start)
                knowledge = await knowledge_store.created_since(day_start)

                daily_payload = DailyRollupData(
                    tier="daily",
                    date=date_str,
                    range_start=target_date.isoformat(),
                    range_end=target_date.isoformat(),
                    sessions=[
                        SessionSummary(
                            id=s.id,
                            what_happened=s.what_happened,
                            for_next_session=s.for_next_session,
                            tags=s.tags,
                            workspace=s.workspace,
                            created_at=s.created_at.isoformat(),
                            updated_at=s.updated_at.isoformat(),
                        )
                        for s in sessions
                    ],
                    messages=messages,
                    memories=[EntityStub(type=e.type.value, content=(e.content or "")[:300], tags=e.tags) for e in entities],
                    knowledge=[KnowledgeStub(topic=k.topic, content=(k.content or "")[:300], tags=k.tags) for k in knowledge],
                )
                return ModelResponse(daily_payload)

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
                raise ValueError(f"Unknown tier: {tier}")

            stories_in_range = await story_store.find_by_period(range_start or "", range_end or "", limit=50)
            if source_tier:
                stories_in_range = [s for s in stories_in_range if s.tier == source_tier]

            tier_payload = TierRollupData(
                tier=tier,
                date=date_str,
                source_tier=source_tier.value if source_tier else None,
                range_start=range_start,
                range_end=range_end,
                stories=stories_in_range,
            )
            return ModelResponse(tier_payload)
        except Exception as e:
            return ExceptionResponse(e)
