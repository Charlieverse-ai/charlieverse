"""Markdown stripping — convert markdown-formatted text to plain text."""

from __future__ import annotations

# Re-export from helpers.text for backwards compatibility
from charlieverse.helpers.text import strip_markdown

__all__ = ["strip_markdown"]
