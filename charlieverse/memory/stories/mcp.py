"""MCP tools: upsert_story, list_stories, get_story, delete_story, get_story_data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.db.stores.context import StoreContext
from charlieverse.mcp.context import _stores
from charlieverse.mcp.responses import PermalinkResponse
from charlieverse.memory.sessions import NewSession, SessionId
from charlieverse.types.dates import UTCDatetime, at_utc_midnight, to_local
from charlieverse.types.lists import TagList
from charlieverse.types.strings import MediumDescription, NonEmptyString, ShortDescription, ShortString

from .models import DeleteStory, NewStory, StoryId, StoryTier
from .store import StoryStore

server = FastMCP(name="Stories")


@server.tool
async def upsert_story(
    title: ShortString,
    content: MediumDescription,
    tier: StoryTier,
    period_start: date,
    period_end: date,
    summary: ShortDescription,
    session_id: SessionId,
    workspace: NonEmptyString,
    tags: TagList,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Create or update a story. For session stories, matches on session_id."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]
    sessions_store = stores["sessions"]

    existing_session = await sessions_store.get(session_id)
    if not existing_session:
        await sessions_store.create(NewSession(id=session_id, workspace=workspace))

    story = NewStory(
        title=title,
        summary=summary,
        content=content,
        tier=tier,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        workspace=workspace,
        session_id=session_id,
        tags=tags,
    )
    result = await story_store.upsert(story)
    return PermalinkResponse("story", result.id)


@server.tool
async def list_stories(
    tier: StoryTier | None = None,
    limit: int = 20,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """List stories, optionally filtered by tier (session, daily, weekly, monthly, all-time)."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    stories = await story_store.list(tier=tier, limit=limit)
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


@server.tool
async def get_story(id: StoryId, ctx: Context = CurrentContext()) -> dict[str, Any]:
    """Get a story by ID. Returns full content."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    story = await story_store.get(id)
    if not story:
        raise ToolError(f"Story {id!s} not found")

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


@server.tool
async def delete_story(id: StoryId, ctx: Context = CurrentContext()) -> dict[str, Any]:
    """Soft-delete a story."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    story = await story_store.get(id)
    if not story:
        raise ToolError(f"Story {id!s} not found")

    await story_store.delete(DeleteStory(id=id))
    return {"deleted": True, "id": str(id)}


@server.tool
async def get_story_data(
    target: str,
    ctx: Context = CurrentContext(),
) -> dict[str, Any]:
    """Get data for the Storyteller to generate a story.

    Args:
        target: Either a session_id (UUID) for session stories,
                or a tier name (daily, weekly, monthly) for rollups.
                Rollups return lower-tier stories for synthesis.
    """
    if not target.strip():
        raise ToolError("target cannot be empty")

    stores = _stores(ctx)
    tier_names = {"daily", "weekly", "monthly", "quarterly", "yearly"}

    if target in tier_names:
        return await _rollup_story_data(stores, target)
    return await _session_story_data(stores, SessionId(target))


async def _rollup_story_data(stores: StoreContext, target: str) -> dict[str, Any]:
    """Build the story-data payload for a rollup tier (daily/weekly/monthly/...)."""
    story_store: StoryStore = stores["stories"]
    today = date.today()

    if target == "daily":
        return await _daily_rollup_data(stores, today)

    source_tier: StoryTier | None = None
    range_start: str | None = None
    range_end: str | None = None

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

    result: dict[str, Any] = {
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

    # Fallback: no lower-tier stories exist for the period → send raw sessions.
    if not stories and range_start and range_end:
        sessions_store = stores["sessions"]
        sessions = await sessions_store.recent_within_range(range_start, range_end)
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


async def _daily_rollup_data(stores: StoreContext, today: date) -> dict[str, Any]:
    """Build the daily story-data payload — sessions + messages + memories + knowledge."""
    sessions_store = stores["sessions"]
    memories_store = stores["memories"]
    knowledge_store = stores["knowledge"]

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

    today_start = at_utc_midnight(today)
    entities = await memories_store.created_since(today_start)
    knowledge = await knowledge_store.created_since(today_start)

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
        "memories": [{"type": e.type.value, "content": (e.content or "")[:300], "tags": e.tags} for e in entities],
        "knowledge": [{"topic": k.topic, "content": (k.content or "")[:300], "tags": k.tags} for k in knowledge],
    }


async def _session_story_data(stores: StoreContext, session_id: SessionId) -> dict[str, Any]:
    """Build the session story-data payload — messages + memories since last save."""
    story_store: StoryStore = stores["stories"]
    sessions_store = stores["sessions"]
    memories_store = stores["memories"]

    session = await sessions_store.get(session_id)
    existing_story = await story_store.find_by_session(session_id)
    since: UTCDatetime | None = existing_story.updated_at if existing_story else None

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
                "seconds_between": seconds_between,
            }
        )

    entities = await memories_store.for_session(session_id)

    return {
        "type": "session",
        "session_id": str(session_id),
        "workspace": session.workspace if session else None,
        "existing_story": {
            "title": existing_story.title,
            "summary": existing_story.summary,
            "content": existing_story.content,
        }
        if existing_story
        else None,
        "messages": messages,
        "memories": [{"type": e.type.value, "content": (e.content or "")[:300], "tags": e.tags} for e in entities],
    }
