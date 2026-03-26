"""Markdown stripping — convert markdown-formatted text to plain text."""

from __future__ import annotations

import re


def strip_markdown(text: str) -> str:
    """Remove common markdown formatting and return plain text.

    Handles: headers, bold/italic, code fences, inline code, links,
    images, bullet/numbered lists, horizontal rules, blockquotes,
    and collapses excessive whitespace.
    """
    if not text:
        return text

    s = text

    # Code fences (```lang\n...\n```) — keep inner content
    s = re.sub(r"```[^\n]*\n(.*?)```", r"\1", s, flags=re.DOTALL)

    # Inline code (`...`) — keep inner content
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # Images ![alt](url) — keep alt text
    s = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", s)

    # Links [text](url) — keep link text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    # Headers (# to ######) — keep text
    s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)

    # Bold/italic (***text***, **text**, *text*, ___text___, __text__, _text_)
    s = re.sub(r"\*{3}(.+?)\*{3}", r"\1", s)
    s = re.sub(r"\*{2}(.+?)\*{2}", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"_{3}(.+?)_{3}", r"\1", s)
    s = re.sub(r"_{2}(.+?)_{2}", r"\1", s)
    # Single underscores only between word boundaries to avoid false positives
    s = re.sub(r"(?<=\s)_(.+?)_(?=\s|$)", r"\1", s)

    # Strikethrough ~~text~~
    s = re.sub(r"~~(.+?)~~", r"\1", s)

    # Horizontal rules (---, ***, ___)
    s = re.sub(r"^[-*_]{3,}\s*$", "", s, flags=re.MULTILINE)

    # Blockquotes (> text) — keep text
    s = re.sub(r"^>\s?", "", s, flags=re.MULTILINE)

    # Unordered list markers (-, *, +)
    s = re.sub(r"^[\s]*[-*+]\s+", "", s, flags=re.MULTILINE)

    # Ordered list markers (1. 2. etc)
    s = re.sub(r"^[\s]*\d+\.\s+", "", s, flags=re.MULTILINE)

    # HTML tags (basic — not a full parser)
    s = re.sub(r"<[^>]+>", "", s)

    # Collapse multiple blank lines into one
    s = re.sub(r"\n{3,}", "\n\n", s)

    # Collapse multiple spaces into one
    s = re.sub(r" {2,}", " ", s)

    return s.strip()
