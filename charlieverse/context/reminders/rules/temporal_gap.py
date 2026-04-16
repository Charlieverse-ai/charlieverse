"""Temporal gap reminder — fires when there's been a significant gap since last message."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.helpers.time_utils import relative_time_seconds


class TemporalGapRule(ReminderRule):
    tag = ReminderTag.TEMPORAL_CONTEXT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        message_gap = int(ctx.metadata.get("last_user_message") or 0)

        if not message_gap:
            return None

        gap_text = relative_time_seconds(message_gap)

        return self.result(
            self.template.render(
                "temporal-gap",
                {"TIME_SINCE": gap_text},
            )
        )
