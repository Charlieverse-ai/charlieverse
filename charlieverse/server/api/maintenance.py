"""Maintenance REST endpoints — index rebuilds and other one-shot operations."""

from __future__ import annotations

from asyncio import gather

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.memory.stores import Stores
from charlieverse.server.responses import (
    ExceptionResponse,
    SavedResponse,
)


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    @mcp.custom_route("/api/rebuild", methods=["POST"])
    async def api_rebuild(request: Request) -> SavedResponse | ExceptionResponse:
        """Rebuild FTS and vector indexes across every store.

        Exposes the same rebuild path the server runs on startup, so the Settings
        page in the dashboard can trigger it on demand without a process restart.
        """
        try:
            await rest_stores.stories.dedupe()
            await gather(
                rest_stores.memories.rebuild(),
                rest_stores.knowledge.rebuild(),
                rest_stores.stories.rebuild(),
                rest_stores.messages.rebuild(),
            )
            return SavedResponse()
        except Exception as e:
            return ExceptionResponse(e)
