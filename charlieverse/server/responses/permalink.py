"""Returns a permalink to an entity in the dashboard."""

from fastmcp.tools import ToolResult
from mcp.types import TextContent

from charlieverse.types.id import ModelId


class PermalinkResponse(ToolResult):
    def __init__(self, kind: str, id: ModelId):
        from charlieverse.config import config

        super().__init__([TextContent(type="text", text=f"{config.server.dashboard_url()}{kind}/{id}")])
