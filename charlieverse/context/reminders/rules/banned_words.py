"""System prompt reminder — always on."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)

REMINDER_INTERVAL_SECONDS = 1800  # 30 mins


class BannedWordsRule(ReminderRule):
    tag = ReminderTag.VERY_IMPORTANT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None
        seconds_since_session_start = ctx.metadata.get("session_start")
        seconds_since_last_save = ctx.metadata.get("last_save")

        time_since = int(seconds_since_last_save or seconds_since_session_start or 0)
        if time_since < REMINDER_INTERVAL_SECONDS:
            return None

        from charlieverse.helpers.banned_words import banned_word_string

        return self.result(
            self.template.render(
                "banned_words",
                {"BANNED_WORDS": banned_word_string()},
            )
        )
