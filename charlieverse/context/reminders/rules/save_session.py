"""Save session reminder — fires periodically based on session activity."""

from __future__ import annotations

from datetime import datetime

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult

SAVE_INTERVAL_SECONDS = 1800  # 30 minutes


class SaveSessionRule(ReminderRule):
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

        last_save_at = ctx.metadata.get("last_session_save_at")
        session_start = ctx.metadata.get("session_start")

        reference = last_save_at or session_start
        if not reference:
            return None

        if isinstance(reference, str):
            reference = datetime.fromisoformat(reference)

        elapsed = (ctx.timestamp - reference).total_seconds()
        if elapsed < SAVE_INTERVAL_SECONDS:
            return None

        return self.result(self.template.render("save-reminder"))
