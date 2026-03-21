"""Shared helpers for accessing stores from MCP context and building permalinks."""

from __future__ import annotations

from fastmcp import Context

from charlieverse.config import config


def _stores(ctx: Context) -> dict:
    return ctx.lifespan_context


def _permalink(kind: str, id: str) -> str:
    """Build a web UI permalink URL."""
    return f"{config.server.dashboard_url()}{kind}/{id}"


async def _remember_with_url(result, kind: str = "memories") -> dict:
    """Wrap a remember_* result to include a permalink URL."""
    return {"id": str(result.id), "url": _permalink(kind, str(result.id))}
