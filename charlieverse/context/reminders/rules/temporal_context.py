"""Temporal context reminder — always on, provides current time and session duration."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.helpers.time_utils import format_datetime, relative_time_seconds


class TemporalContextRule(PromptSubmitReminder):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        context = self.context(ctx)
        if not context:
            return None

        if context.message_count.total.messages < 5:
            return None

        template_vars: dict[str, str] = {
            "CURRENT_DATETIME": format_datetime(ctx.timestamp),
            "SAVE": "You have NOT saved yet this session!!",
            "TIME_SINCE_LAST_MESSAGE": "_no idea_",
        }

        last_message = context.last_user_message
        if last_message:
            template_vars["TIME_SINCE_LAST_MESSAGE"] = relative_time_seconds(last_message)

        session_save = context.last_save
        if session_save:
            template_vars["SAVE"] = (
                f"It's been {relative_time_seconds(session_save)}, {context.message_count.since_last_save.messages} messages, and {context.message_count.since_last_save.turns} turns since you last saved."
            )

        return self.result(self.template.render("temporal-context", template_vars))
