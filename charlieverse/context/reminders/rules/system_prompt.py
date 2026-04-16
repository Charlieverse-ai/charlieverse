"""System prompt reminder — always on."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)


class SystemPromptRule(ReminderRule):
    tag = ReminderTag.VERY_IMPORTANT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

        message_count = ctx.metadata.get("message_count") or 0

        if message_count % 5 == 0:
            return self.result(self.template.render("system-prompt"))
