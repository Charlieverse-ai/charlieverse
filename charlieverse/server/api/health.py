"""REST hook endpoints: session lifecycle, heartbeat, health, work-logs, messages, context enrich."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def register_routes(mcp: FastMCP) -> None:
    @mcp.custom_route("/api/health", methods=["GET"])
    async def api_health(request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({"status": "healthy", "server": "charlieverse"})
