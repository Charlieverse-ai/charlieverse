"""REST API route modules for Charlieverse."""

from fastmcp import FastMCP

from charlieverse.memory.stores import Stores

from . import dashboard, entities, health, hooks, knowledge, messages, search, sessions, stats, stories


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    health.register_routes(mcp)
    entities.register_routes(mcp, rest_stores)
    hooks.register_routes(mcp, rest_stores)
    knowledge.register_routes(mcp, rest_stores)
    search.register_routes(mcp, rest_stores)
    sessions.register_routes(mcp, rest_stores)
    stats.register_routes(mcp, rest_stores)
    stories.register_routes(mcp, rest_stores)
    messages.register_routes(mcp, rest_stores)

    # Catch all for single page app, needs to be last
    dashboard.register_routes(mcp)
