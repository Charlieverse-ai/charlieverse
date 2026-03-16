"""Generate story reminder — fires when it's time to create a new story."""

from __future__ import annotations

from datetime import datetime

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult

# TODO: Check actual last story generation date from the DB.
# For now, fires on every UserPromptSubmit as a placeholder
# until we wire up the story date check.


class GenerateStoryRule(ReminderRule):
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

        next_story_date = ctx.metadata.get("next_story_date")
        if not next_story_date:
            return self.result(self.template.render("generate-story"))

        if isinstance(next_story_date, str):
            next_story_date = datetime.fromisoformat(next_story_date)

        if ctx.timestamp >= next_story_date:
            return self.result(self.template.render("generate-story"))

        return None
