"""Temporal gap reminder — fires when there's been a significant gap since last message."""

from __future__ import annotations

from datetime import datetime

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.context.time_utils import _normalize_tz, relative_time

GAP_THRESHOLD_SECONDS = 300  # 5 minutes


class TemporalGapRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        last_response_at = ctx.metadata.get("last_assistant_response_at")
        if not last_response_at:
            return None

        if isinstance(last_response_at, str):
            last_response_at = datetime.fromisoformat(last_response_at)

        gap_seconds = (_normalize_tz(ctx.timestamp) - _normalize_tz(last_response_at)).total_seconds()
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
