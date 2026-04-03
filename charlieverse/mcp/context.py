"""Shared helpers for accessing stores from MCP context and building permalinks."""

from __future__ import annotations

from fastmcp import Context

from charlieverse.config import config
from charlieverse.db.stores.context import StoreContext


def _stores(ctx: Context) -> StoreContext:
    return ctx.lifespan_context  # type: ignore[return-value]


def _permalink(kind: str, id: str) -> str:
    """Build a web UI permalink URL."""
    return f"{config.server.dashboard_url()}{kind}/{id}"


async def _remember_with_url(result, kind: str = "memories") -> dict:
    """Wrap a remember_* result to include a permalink URL."""
    return {"url": _permalink(kind, str(result.id))}
