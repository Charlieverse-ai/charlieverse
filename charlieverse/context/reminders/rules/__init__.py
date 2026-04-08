"""Rule registry — creates all reminder rules."""

from __future__ import annotations

from charlieverse.context.reminders.rules.banned_words import BannedWordsRule
from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.rules.save_session import SaveSessionRule
from charlieverse.context.reminders.rules.search_memories import SearchMemoriesRule
from charlieverse.context.reminders.rules.system_prompt import SystemPromptRule
from charlieverse.context.reminders.rules.temporal_context import TemporalContextRule
from charlieverse.context.reminders.rules.temporal_gap import TemporalGapRule
from charlieverse.context.reminders.template import ReminderTemplate


def register_rules(template: ReminderTemplate | None = None) -> list[ReminderRule]:
    """Create and return all reminder rules with a shared template renderer."""
    t = template or ReminderTemplate()
    return [
        TemporalContextRule(t),
        SystemPromptRule(t),
        TemporalGapRule(t),
        SaveSessionRule(t),
        SearchMemoriesRule(t),
        BannedWordsRule(t),
    ]
