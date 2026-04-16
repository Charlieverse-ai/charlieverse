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
            "TIME_SINCE_SAVE": "never",
        }

        vars["RELATIVE_TIME_SINCE_SESSION_START"] = relative_time_seconds(int(ctx.metadata.get("session_start") or 0))

        session_save = ctx.metadata.get("last_save")
        if session_save:
            vars["TIME_SINCE_SAVE"] = relative_time_seconds(int(session_save))

        return self.result(self.template.render("temporal-context", vars))
