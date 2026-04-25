"""Returns a permalink to an entity in the dashboard."""

from fastmcp.tools import ToolResult
from mcp.types import TextContent

from charlieverse.types.id import ModelId


class PermalinkResponse(ToolResult):
    """ToolResult that returns a dashboard permalink as both a TextContent block
    and a structured payload.

    The structured payload is required because FastMCP auto-generates an
    outputSchema from this return type, and MCP clients (notably Claude Code's
    response validator) reject responses with a declared outputSchema but no
    structured_content. Providing a structured_content dict satisfies the
    validator and gives clients a machine-readable handle on the saved entity.
    """

    def __init__(self, kind: str, id: ModelId):
        from charlieverse.config import config

        url = f"{config.server.dashboard_url()}{kind}/{id}"
        super().__init__(
            content=[TextContent(type="text", text=url)],
            structured_content={"kind": kind, "id": str(id), "url": url},
        )
