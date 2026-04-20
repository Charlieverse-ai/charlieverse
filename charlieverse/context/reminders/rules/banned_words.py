"""Periodic banned-words reminder — fires every 20 total turns as a baseline drip."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)

# How often the baseline reminder fires (in total session turns).
# Offset from SaveSessionRule's 15-turn cadence so they don't pile up.
PERIODIC_INTERVAL = 20


class BannedWordsRule(PromptSubmitReminder):
    tag = ReminderTag.VERY_IMPORTANT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        context = self.context(ctx)
        if not context:
            return None
        turns = context.message_count.total.turns
        if turns <= 0 or turns % PERIODIC_INTERVAL != 0:
            return None

        from charlieverse.helpers.banned_words import banned_word_string

        return self.result(
            self.template.render(
                "banned_words",
                {"BANNED_WORDS": banned_word_string()},
            )
        )
