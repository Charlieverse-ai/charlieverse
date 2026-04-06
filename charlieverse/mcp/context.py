"""Shared helpers for accessing stores from MCP context and building permalinks."""

from __future__ import annotations

from fastmcp import Context

from charlieverse.memory.stores import Stores


def _stores(ctx: Context) -> Stores:
    return Stores.from_context(ctx.lifespan_context)
