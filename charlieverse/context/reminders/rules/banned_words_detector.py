"""Reactive banned-words reminder — fires when the previous assistant message
contained a banned phrase. Yells at Charlie with the matches and the full list."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)


class BannedWordsDetectorRule(PromptSubmitReminder):
    """Catch banned-word violations in the previous assistant turn and yell."""

    tag = ReminderTag.VERY_IMPORTANT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        context = self.context(ctx)
        if not context:
            return None

        from charlieverse.helpers.banned_words import (
            check_text,
            format_feedback,
        )

        last_assistant = context.last_assistant_message
        if not last_assistant:
            return None

        matches = check_text(last_assistant)
        if not matches:
            return None

        return self.result(
            self.template.render(
                "banned-words-violation",
                {"MATCHED_WORDS": format_feedback(matches)},
            )
        )
