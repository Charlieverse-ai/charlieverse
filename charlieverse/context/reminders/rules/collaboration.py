"""Collaboration reminder — always on."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult


class CollaborationRule(ReminderRule):
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        return self.result(self.template.render("collaboration"))
