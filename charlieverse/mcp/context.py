"""Shared helpers for accessing stores from MCP context and building permalinks."""

from __future__ import annotations

from typing import TypedDict

import aiosqlite
from fastmcp import Context

from charlieverse.config import config
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, StoryStore


class StoreContext(TypedDict):
    """Typed lifespan context passed to every MCP tool via ctx.lifespan_context."""

    db: aiosqlite.Connection
    memories: MemoryStore
    knowledge: KnowledgeStore
    sessions: SessionStore
    stories: StoryStore


def _stores(ctx: Context) -> StoreContext:
    return ctx.lifespan_context  # type: ignore[return-value]


def _permalink(kind: str, id: str) -> str:
    """Build a web UI permalink URL."""
    return f"{config.server.dashboard_url()}{kind}/{id}"


async def _remember_with_url(result, kind: str = "memories") -> dict:
    """Wrap a remember_* result to include a permalink URL."""
    return {"url": _permalink(kind, str(result.id))}
