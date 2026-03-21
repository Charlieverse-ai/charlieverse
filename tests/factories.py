"""Test factories — lightweight builders for domain objects used in tests."""

from __future__ import annotations

from typing import Any


def make_entity(
    type: str = "decision",
    content: str = "test decision",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a dict of kwargs for remember_* tool calls.

    Keys mirror the common parameters accepted by remember_decision,
    remember_solution, etc.  Callers pass the result directly as **kwargs.
    """
    base: dict[str, Any] = {
        "type": type,
        "content": content,
        "tags": None,
        "pinned": False,
        "session_id": None,
    }
    base.update(overrides)
    return base


def make_knowledge(
    topic: str = "test topic",
    content: str = "test content",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a dict of kwargs for update_knowledge tool calls."""
    base: dict[str, Any] = {
        "topic": topic,
        "content": content,
        "tags": None,
        "pinned": False,
        "session_id": None,
    }
    base.update(overrides)
    return base


def make_story(
    title: str = "test story",
    content: str = "test content",
    tier: str = "session",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a dict of kwargs for upsert_story tool calls."""
    base: dict[str, Any] = {
        "title": title,
        "content": content,
        "tier": tier,
        "period_start": "2026-03-01",
        "period_end": "2026-03-20",
        "summary": None,
        "tags": None,
        "workspace": None,
        "session_id": None,
    }
    base.update(overrides)
    return base
