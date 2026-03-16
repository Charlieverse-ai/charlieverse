"""Generate story reminder — nudges to run /session-save."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import HookContext, ReminderResult

# Fires when session has been going for a while without a story save.
# Works alongside save_session rule but with a different message.
STORY_NUDGE_INTERVAL_SECONDS = 3600  # 1 hour


class GenerateStoryRule(ReminderRule):
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

        session_start = ctx.metadata.get("session_start")
        if not session_start:
            # No session timing info — still fire the reminder
            return self.result(self.template.render("generate-story"))

        from datetime import datetime

        if isinstance(session_start, str):
            session_start = datetime.fromisoformat(session_start)

        elapsed = (ctx.timestamp - session_start).total_seconds()
        if elapsed < STORY_NUDGE_INTERVAL_SECONDS:
            return None

        return self.result(self.template.render("generate-story"))
