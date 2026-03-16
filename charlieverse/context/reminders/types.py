"""Types for the reminders context system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReminderTag(Enum):
    """XML tag used to wrap reminder content in additionalContext."""

    VERY_IMPORTANT = "very-important"
    CHARLIE_REMINDER = "charlie-reminder"
    SYSTEM_REMINDER = "system-reminder"
    TEMPORAL_CONTEXT = "temporal-context"


@dataclass
class ReminderResult:
    """Output from a rule that fired."""

    content: str
    tag: ReminderTag


@dataclass
class HookContext:
    """Context passed from a hook event into the reminders engine.

    The hook command populates this from stdin JSON + any pre-fetched data.
    Rules use it to decide whether to fire and what variables to substitute.
    """

    event: str  # "UserPromptSubmit", "PreToolUse", "PostToolUse", etc.
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str | None = None
    message: str | None = None
    tool_name: str | None = None
    tool_input: dict | None = None
    metadata: dict = field(default_factory=dict)
