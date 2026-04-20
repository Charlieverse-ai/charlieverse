"""System prompt reminder — re-injects the voice guardrails every N turns."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)

PERIODIC_INTERVAL = 30


class SystemPromptRule(PromptSubmitReminder):
    tag = ReminderTag.VERY_IMPORTANT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        context = self.context(ctx)
        if not context:
            return None
        turns = context.message_count.total.turns
        if turns <= 0 or turns % PERIODIC_INTERVAL != 0:
            return None

        return self.result(self.template.render("system-prompt"))
