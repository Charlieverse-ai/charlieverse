from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import CurrentContext

from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import ModelListResponse
from charlieverse.types.strings import ShortString

server = FastMCP(name="Messages")


@server.tool
async def search_messages(
    query: ShortString,
    limit: int = 20,
    session_id: SessionId | None = None,
    ctx: Context = CurrentContext(),
) -> ModelListResponse | None:
    """Search past messages in conversations. Returns matching messages with role and date."""
    if not query.strip():
        raise ToolError("query cannot be empty")
    store = Stores.from_context(ctx).messages

    results = await store.search(query, limit=limit, session_id=session_id)

    if not results:
        return

    return ModelListResponse(results)
