from __future__ import annotations

from datetime import date

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.memory.sessions import NewSession, SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString, WorkspaceFilePath

from .models import DeleteStory, NewStory, StoryId, StoryTier
from .store import StoryStore

server = FastMCP(name="Stories")


@server.tool
async def save_story(
    title: NonEmptyString,
    content: NonEmptyString,
    tier: StoryTier,
    period_start: date,
    period_end: date,
    summary: NonEmptyString,
    session_id: SessionId,
    workspace: WorkspaceFilePath,
    tags: TagList,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Create or update a story. For session stories, matches on session_id."""
    stores = Stores.from_context(ctx)
    story_store: StoryStore = stores.stories
    sessions_store = stores.sessions

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
async def forget_story(
    id: StoryId,
    ctx: Context = CurrentContext(),
) -> None:
    """Forget a story."""
    story_store = Stores.from_context(ctx).stories

    story = await story_store.get(id)
    if not story:
        raise ToolError(f"Story {id!s} not found")

    await story_store.delete(DeleteStory(id=id))
