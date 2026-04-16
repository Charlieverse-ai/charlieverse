"""MCP tools: search_messages, session_update."""

from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import CurrentContext

from charlieverse.context import ActivationBuilder
from charlieverse.context.renderer import ActivationContextRenderer
from charlieverse.memory.sessions import NewSession
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.types.lists import TagList
from charlieverse.types.strings import WorkspaceFilePath

from .models import SessionContent, SessionId

server = FastMCP(name="Sessions")


@server.tool(annotations={"readOnlyHint": True})
async def activation_context(
    workspace: WorkspaceFilePath,
    session_id: SessionId,
    ctx: Context = CurrentContext(),
) -> str:
    stores = Stores.from_context(ctx)
    session_store: SessionStore = stores.sessions
    session = await session_store.get(SessionId(session_id))

    if not session:
        session = await session_store.create(NewSession(workspace=workspace))

    bundle = await ActivationBuilder(stores).build(session_id, workspace)

    return ActivationContextRenderer(bundle).render()


@server.tool
async def update_session(
    session_id: SessionId,
    workspace: WorkspaceFilePath,
    content: SessionContent | None = None,
    tags: TagList | None = None,
    ctx: Context = CurrentContext(),
) -> PermalinkResponse:
    """Update the session with the provided fields. Omit a field to keep the existing value"""
    from .models import UpdateSession

    session_store: SessionStore = Stores.from_context(ctx).sessions

    session = UpdateSession(
        id=session_id,
        content=content,
        tags=tags,
        workspace=workspace,
    )

    await session_store.upsert(session)
    return PermalinkResponse("sessions", session_id)
