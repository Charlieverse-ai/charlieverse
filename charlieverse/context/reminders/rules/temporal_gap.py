"""Temporal gap reminder — fires when there's been a significant gap since last message."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.context.time_utils import relative_time
from charlieverse.types.dates import from_iso

GAP_THRESHOLD_SECONDS = 300  # 5 minutes


class TemporalGapRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        last_response_at_raw = ctx.metadata.get("last_assistant_response_at")
        if not last_response_at_raw:
            return None

        last_response_at = (
            from_iso(last_response_at_raw) if isinstance(last_response_at_raw, str) else last_response_at_raw
        )

        gap_seconds = (ctx.timestamp - last_response_at).total_seconds()
        if gap_seconds < GAP_THRESHOLD_SECONDS:
            return None

        gap_text = relative_time(last_response_at, ctx.timestamp)
        return self.result(
            self.template.render(
                "temporal-gap",
                {
                    "TIME_SINCE": gap_text,
                },
            )
        )
