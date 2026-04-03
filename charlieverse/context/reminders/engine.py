"""Reminders engine — evaluates rules and assembles context output."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from charlieverse.context.reminders.rules import register_rules
from charlieverse.context.reminders.rules.base import ReminderRule
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)


class RemindersEngine:
    """Evaluates all registered reminder rules against a hook context.

    The engine is the entry point for hooks. Pass in a HookContext,
    get back formatted reminder output ready for injection
    into additionalContext.
    """

    def __init__(self, rules: list[ReminderRule] | None = None) -> None:
        self.rules = rules or register_rules()

    async def process(self, ctx: HookContext) -> list[ReminderResult]:
        """Run all rules against the context, return results that fired.

        Rules are evaluated concurrently. Failures are silently skipped.
        """
        raw_results = await asyncio.gather(
            *(rule.evaluate(ctx) for rule in self.rules),
            return_exceptions=True,
        )
        results: list[ReminderResult] = [r for r in raw_results if not isinstance(r, BaseException) and r is not None]
        return results

    def format(self, results: list[ReminderResult]) -> str:
        """Group results by tag, wrap each group in a single XML block."""
        grouped: dict[ReminderTag, list[str]] = defaultdict(list)
        filtered = [result for result in results if result.content.strip()]
        for result in filtered:
            grouped[result.tag].append(result.content)

        parts: list[str] = []
        for tag, contents in grouped.items():
            inner = "\n".join(contents)
            parts.append(f"<{tag.value}>{inner}</{tag.value}>")

        return "\n".join(parts)
