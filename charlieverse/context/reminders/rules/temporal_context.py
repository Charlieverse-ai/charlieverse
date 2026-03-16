"""Temporal context reminder — always on, provides current time and session duration."""

from __future__ import annotations

from datetime import datetime

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult, ReminderTag
from charlieverse.context.time_utils import format_datetime, relative_time


class TemporalContextRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        vars: dict[str, str] = {
            "CURRENT_DATETIME": format_datetime(ctx.timestamp),
        }

        session_start = ctx.metadata.get("session_start")
        if session_start:
            if isinstance(session_start, str):
                session_start = datetime.fromisoformat(session_start)
            vars["RELATIVE_TIME_SINCE_SESSION_START"] = relative_time(session_start, ctx.timestamp)

        return self.result(self.template.render("temporal-context", vars))
