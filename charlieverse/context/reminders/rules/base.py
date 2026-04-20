"""Base class for reminder rules."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from charlieverse.context.reminders.template import ReminderTemplate
from charlieverse.context.reminders.types import (
    HookContext,
    ReminderResult,
    ReminderTag,
)
from charlieverse.server.responses.prompt_submit_delta import PromptSubmitContext

logger = logging.getLogger(__name__)


class ReminderRule(ABC):
    """A single reminder rule that decides whether to fire and returns content.

    Each rule gets the HookContext and a shared ReminderTemplate renderer.
    The rule decides if it applies to this context, and if so, loads its
    template file and returns a ReminderResult with content + tag.

    Subclasses can override `tag` to control how their output is wrapped.
    """

    tag: ReminderTag = ReminderTag.VERY_IMPORTANT
    events: list[str] | None = None

    def __init__(self, template: ReminderTemplate) -> None:
        self.template = template

    @abstractmethod
    async def evaluate(self, ctx: HookContext) -> ReminderResult | None:
        """Evaluate this rule against the given context.

        Returns:
            ReminderResult if the rule fires, None otherwise.
        """
        ...

    def result(self, content: str) -> ReminderResult:
        """Convenience: wrap content with this rule's tag."""
        return ReminderResult(content=content, tag=self.tag)


class PromptSubmitReminder(ReminderRule):
    def __init__(self, template: ReminderTemplate) -> None:
        super().__init__(template)
        self.events = ["UserPromptSubmit"]

    def context(self, ctx: HookContext) -> PromptSubmitContext | None:
        try:
            return PromptSubmitContext.model_validate(ctx.metadata)
        except Exception:
            logger.exception("PromptSubmitContext validation failed; metadata=%r", ctx.metadata)
            return None
