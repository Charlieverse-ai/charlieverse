"""Reminder template loader and renderer."""

from __future__ import annotations

from pathlib import Path
from string import Template

from charlieverse.helpers import paths

REMINDERS_DIR = (paths.prompts() or Path(__file__).parent.parent.parent / "prompts") / "reminders"


class ReminderTemplate:
    """Loads a .md reminder file and substitutes variables via string.Template."""

    def __init__(self, reminders_dir: Path = REMINDERS_DIR) -> None:
        self._dir = reminders_dir

    def render(self, filename: str, vars: dict[str, str] | None = None) -> str:
        """Load prompts/reminders/{filename}.md and substitute variables.

        Args:
            filename: Name without extension, e.g. "temporal-gap"
            vars: Template variables to substitute. Uses safe_substitute
                  so unresolved variables stay as-is rather than erroring.

        Returns:
            Rendered reminder content.

        Raises:
            FileNotFoundError: If the reminder file doesn't exist.
        """
        path = self._dir / f"{filename}.md"
        content = path.read_text().strip()
        if vars:
            return Template(content).safe_substitute(vars)
        return content
