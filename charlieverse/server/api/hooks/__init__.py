"""REST hook endpoints: session lifecycle, heartbeat, health, work-logs, messages, context enrich."""

from __future__ import annotations

from fastmcp import FastMCP

from charlieverse.memory.stores import Stores

from . import enrich_context, sessions


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register hook REST endpoints on the given FastMCP instance."""
    enrich_context.register_routes(mcp, rest_stores)
    sessions.register_routes(mcp, rest_stores)
