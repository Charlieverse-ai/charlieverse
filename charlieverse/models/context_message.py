"""Lightweight message model for context seeding."""

from __future__ import annotations

from dataclasses import dataclass

from charlieverse.types.dates import UTCDatetime


@dataclass(frozen=True)
class ContextMessage:
    """A message for context seeding — stripped down, no tool content."""

    role: str  # "user" or "assistant"
    content: str
    created_at: UTCDatetime
