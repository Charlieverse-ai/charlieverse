"""Memory search rule — extracts entities from messages and injects relevant memories."""

from __future__ import annotations

from typing import Literal

from charlieverse.context.reminders.rules.base import PromptSubmitReminder
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.helpers.text import strip_markdown
from charlieverse.server.responses.summaries import EntitySummary


class SearchMemoriesRule(PromptSubmitReminder):
    tag: Literal[ReminderTag.MEMORY_HINT] = ReminderTag.MEMORY_HINT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if not ctx.message or len(ctx.message.strip()) < 5:
            return None

        import httpx

        from charlieverse.config import config

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    config.server.api_url("context/enrich"),
                    json={
                        "text": ctx.message,
                        "session_id": ctx.session_id,
                        "seen_ids": ctx.metadata.get("seen_memory_ids", []),
                    },
                )
                if resp.status_code != 200:
                    return None

                data = resp.json()
                if not data or not isinstance(data, list):
                    return None

                parts: list[str] = []
                for e in data:
                    memory = EntitySummary.model_construct(**e)
                    tag = str(memory.type)
                    content = strip_markdown(memory.content.strip())

                    parts.append(f'<{tag} date="{memory.age}">{content}</{tag}>')

                return self.result("\n".join(parts))
        except Exception:
            return None
