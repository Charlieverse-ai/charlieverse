"""Returns a permalink to an entity in the dashboard."""

from pydantic import BaseModel

from charlieverse.types.id import ModelId


class PermalinkResponse(BaseModel):
    """Permalink payload returned by MCP write-tools.

    A plain Pydantic model — NOT a fastmcp ToolResult subclass. FastMCP
    auto-generates an outputSchema from the tool's return type annotation; if
    the return type is a ToolResult subclass, the schema leaks transport
    fields (content / structured_content / meta) and MCP clients (notably
    Claude Code's response validator) reject responses where any of those
    required envelope fields is missing or shaped wrong.

    Returning a Pydantic model instead lets FastMCP:
      * derive an outputSchema describing just {kind, id, url}
      * wrap the value in a ToolResult internally with structured_content set
        to model.model_dump() and content set to the JSON text
      * keep the response shape stable across MCP clients
    """

    kind: str
    id: str
    url: str

    @classmethod
    def for_entity(cls, kind: str, entity_id: ModelId) -> "PermalinkResponse":
        from charlieverse.config import config

        return cls(
            kind=kind,
            id=str(entity_id),
            url=f"{config.server.dashboard_url()}{kind}/{entity_id}",
        )

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Backwards-compatible positional-args constructor: PermalinkResponse(kind, id).
        # Existing call sites use this shape; preserved so changing the model class
        # doesn't ripple through every MCP tool.
        if args and len(args) == 2 and not kwargs:
            kind = args[0]
            entity_id = args[1]
            assert isinstance(kind, str)
            from charlieverse.config import config

            super().__init__(
                kind=kind,
                id=str(entity_id),
                url=f"{config.server.dashboard_url()}{kind}/{entity_id}",
            )
            return
        # Otherwise behave like a normal Pydantic model.
        super().__init__(*args, **kwargs)
