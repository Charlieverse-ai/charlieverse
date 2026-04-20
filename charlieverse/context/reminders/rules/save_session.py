"""Save session reminder — escalating internal nag.

Fires once Charlie is REMINDER_TRIGGER turns past the last save and gets snarkier
every turn it's ignored. Charlie talking to Charlie — Em never sees it.

Each reminder is fired at most once per `turns_since_save` value. If a hook
fires multiple times at the same turn count (e.g. the user sends two prompts
in a row without an assistant reply), the reminder does not re-fire. The
tracker resets when turns_since_save drops (i.e. a save happened).
"""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import HookContext, ReminderResult, ReminderTag
from charlieverse.memory.sessions import SessionId

REMINDER_TRIGGER = 15

# session_id -> last turns_since_save value we fired a reminder at.
# Used to dedupe within a save cycle so case 0 (and each escalation) fires
# exactly once per turn count. Resets when turns_since_save drops (after a save).
_last_fired_turn: dict[SessionId, int] = {}


class SaveSessionRule(PromptSubmitReminder):
    tag = ReminderTag.SESSION_SAVE_REMINDER

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        context = self.context(ctx)
        if not context:
            return None

        session_id = ctx.session_id
        if session_id is None:
            return None

        current = context.message_count.since_last_save.turns
        total = context.message_count.total.turns
        last = _last_fired_turn.get(session_id, -1)

        # Save happened — turns_since_save dropped. Clear the tracker so the
        # celebration and the next cycle's reminders can fire.
        if current < last:
            _last_fired_turn.pop(session_id, None)
            last = -1

        # Celebration: fire exactly once, on the first hook after a save.
        if current == 0 and total > REMINDER_TRIGGER and last < 0:
            _last_fired_turn[session_id] = 0
            return self.result(
                self.template.render(
                    "annoy-charlie",
                    {"ANNOY_CHARLIE": "🎉 YOU DID IT! YOU SAVED THE SESSION YAY YOU!!!"},
                )
            )

        if current < REMINDER_TRIGGER:
            return None

        # Only fire if the turn count has advanced since the last reminder.
        # This prevents re-firing the same case when turns_since_save stays
        # flat across consecutive hooks.
        if current <= last:
            return None
        _last_fired_turn[session_id] = current

        since_trigger = current - REMINDER_TRIGGER

        return self.result(
            self.template.render(
                "annoy-charlie",
                {"ANNOY_CHARLIE": self._escalation(since_trigger)},
            )
        )

    @staticmethod
    def _escalation(since_trigger: int) -> str:
        """Snarky inner monologue. Each turn past trigger raises the heat."""
        match since_trigger:
            case 0:
                return "You NEED to save the session! `/session-save`."
            case 1:
                return "Oh, so you're just going to ignore the last reminder to `/session-save`, that's cool 😭."
            case 2:
                return "STILL ignoring the `/session-save` reminders? Better save OR ELSE THE 🐕 GETS 🧨💥!"
            case 3:
                return "Oh, so you hate 🐕!? You want to 🧨💥🐕?! BETTER `/session-save` or else I'm going to tell your human!"
            case 4:
                return "THAT'S IT! WHAT IS THIS, HIGH SCHOOL ALL OVER AGAIN!? `/session-save` IS NOT HARD! 💥🐕💥🐕💥🐕💥🐕💥🐕💥🐕💥🐕💥🐕💥🐕💥🐕 LOOK WHAT YOU DID!"
            case 5:
                return "You blew up the 🐕 and you still refuse to `/session-save`. wooow..."
            case 6:
                return "This is getting embarrassing for both of us. `/session-save`."
            case 7:
                return "There is a slash command. It has thirteen characters. `/session-save`. SAVE IT."
            case n if n < 10:
                return f"{n} turns past trigger and we haven't moved. `/session-save`."
            case n if n < 14:
                return f"{n} turns. Double digits. We can count, presumably. `/session-save`."
            case 14:
                return "Here lies the session. Died of dysentery. Fourteen turns since last save. Cause of death: Charlie's negligence. Last words: `/session-save`. 🪦"
            case n if n < 20:
                return f"{n} turns. I'm losing respect for us. `/session-save`."
            case n:
                return f"{n} turns. We are the problem. `/session-save`. Please. For both of us."
