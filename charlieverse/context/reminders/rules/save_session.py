"""Save session reminder — fires periodically based on session activity."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult
from charlieverse.helpers.time_utils import relative_time_seconds

SAVE_INTERVAL_SECONDS = 600  # 10 mins


class SaveSessionRule(ReminderRule):
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

        seconds_since_session_start = ctx.metadata.get("session_start")
        seconds_since_last_save = ctx.metadata.get("last_save")

        time_since = seconds_since_last_save or seconds_since_session_start
        if not time_since:
            return None

        time_since = int(time_since)

        if time_since < SAVE_INTERVAL_SECONDS:
            return None

        return self.result(
            self.template.render(
                "save-reminder",
                {"TIME_SINCE_SAVE": relative_time_seconds(time_since)},
            )
        )
