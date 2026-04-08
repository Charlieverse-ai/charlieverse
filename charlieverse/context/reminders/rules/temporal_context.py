"""Temporal context reminder — always on, provides current time and session duration."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.helpers.time_utils import format_datetime, relative_time_seconds


class TemporalContextRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        vars: dict[str, str] = {
            "CURRENT_DATETIME": format_datetime(ctx.timestamp),
            "RELATIVE_TIME_SINCE_SESSION_START": "Just started.",
            "TIME_SINCE_SAVE": "never",
        }

        session_start = int(ctx.metadata.get("session_start", 0))
        vars["RELATIVE_TIME_SINCE_SESSION_START"] = relative_time_seconds(session_start)

        session_save = int(ctx.metadata.get("last_save", 0))
        if session_save:
            vars["TIME_SINCE_SAVE"] = relative_time_seconds(session_save)

        return self.result(self.template.render("temporal-context", vars))
