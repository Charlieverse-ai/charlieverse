from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.memory.messages import Message
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.types.strings import NonEmptyString

server = FastMCP(name="Messages")


@server.tool(annotations={"readOnlyHint": True})
async def search_conversations(
    query: NonEmptyString,
    limit: int = 20,
    session_id: SessionId | None = None,
    ctx: Context = CurrentContext(),
) -> list[Message] | None:
    """Search past messages in conversations. Returns matching messages with role and date."""
    if not query.strip():
        raise ToolError("query cannot be empty")
    store = Stores.from_context(ctx).messages

    results = await store.search(query, limit=limit, session_id=session_id)

    if not results:
        return

    return results
