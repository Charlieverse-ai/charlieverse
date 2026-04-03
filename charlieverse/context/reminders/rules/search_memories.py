"""Memory search rule — extracts entities from messages and injects relevant memories."""

from __future__ import annotations

from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)


class SearchMemoriesRule(ReminderRule):
    tag = ReminderTag.MEMORY_HINT

    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        if ctx.event != "UserPromptSubmit":
            return None

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
        except Exception:
            return None

        found = data.get("found", [])
        not_found = data.get("not_found", [])
        stories = data.get("stories", [])

        if not found and not not_found and not stories:
            return None

        parts: list[str] = []

        # Inject found memories as context
        if found:
            for group in found:
                for mem in group.get("memories", []):
                    parts.append(f"[{mem['type']}] {mem['content']}")
                for know in group.get("knowledge", []):
                    parts.append(f"[knowledge: {know['topic']}] {know['content']}")

        # Inject matching stories for temporal references
        if stories:
            for story in stories:
                period = f"{story['period_start']} to {story['period_end']}"
                parts.append(f"[story: {story['title']}] ({story['tier']}, {period}) {story['content']}")

        # Hint about entities not found in memories
        if not_found:
            parts.append(f"No memories found for: {', '.join(not_found)}")

        if not parts:
            return None

        return self.result("\n".join(parts))
