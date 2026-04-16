from __future__ import annotations

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool


class MetaMiddleware(Middleware):
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools: list[Tool] = await call_next(context)

        if tools:
            updated_tools: list[Tool] = []
            for tool in tools:
                meta = tool.meta or {}
                meta["anthropic/alwaysLoad"] = True

                tool.meta = meta
                updated_tools.append(tool)

            tools: list[Tool] = updated_tools

        return tools
