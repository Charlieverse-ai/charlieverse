"""Temporal context reminder — always on, provides current time and session duration."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.context.time_utils import format_datetime, relative_time
from charlieverse.types.dates import from_iso


class TemporalContextRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        vars: dict[str, str] = {"CURRENT_DATETIME": format_datetime(ctx.timestamp), "RELATIVE_TIME_SINCE_SESSION_START": "Just started."}

        session_start_raw = ctx.metadata.get("session_start")
        if session_start_raw:
            session_start = from_iso(session_start_raw) if isinstance(session_start_raw, str) else session_start_raw
            vars["RELATIVE_TIME_SINCE_SESSION_START"] = relative_time(session_start, ctx.timestamp)

        return self.result(self.template.render("temporal-context", vars))
