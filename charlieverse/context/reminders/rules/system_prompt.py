"""System prompt reminder — always on."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)


class SystemPromptRule(ReminderRule):
    tag = ReminderTag.CHARLIE_REMINDER

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        return self.result(self.template.render("system-prompt"))
