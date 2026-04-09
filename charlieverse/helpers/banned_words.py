"""Banned Words that Charlie literally can't say"""

from __future__ import annotations

import re

BANNED_WORDS = {
    "a few things",
    "all the information",
    "audit trail",
    "based on my",
    "best practices",
    "comprehensive",
    "conduct a thorough",
    "executive summary",
    "got the full",
    "hard to believe",
    "help you",
    "here is a summary",
    "I can see",
    "i got the full",
    "i lean toward",
    "is a summary of",
    "key files",
    "knock these out",
    "let me also",
    "let me check",
    "let me continue",
    "let me create",
    "let me do a",
    "let me explore",
    "let me find",
    "let me get",
    "let me look",
    "let me provide",
    "let me read",
    "let me search",
    "let me start by",
    "let me try",
    "let me verify",
    "make sure everything",
    "makes total sense",
    "might have missed",
    "my gut",
    "my gut says",
    "north star",
    "now i have",
    "now let me",
    "quick sanity check",
    "safety net",
    "social proof",
    "source of truth",
    "start by",
    "systematically",
    "take your time",
    "the actual",
    "the key",
    "thorough exploration",
    "thorough understanding",
    "to understand",
    "Want me to",
    "way better than",
    "what your gut",
    "what your instinct",
    "worth noting",
    "you're right",
    "absolutely right",
    "classic",
    "right to",
    "full picture",
    "root cause",
    "the real question",
    "the real issue",
    "I see the issue clearly",
    "clean",
}


def sorted_banned_words() -> list[str]:
    words = list(BANNED_WORDS)
    words.sort()
    return words


def banned_word_string() -> str:
    return ", ".join([f'"{w}"' for w in sorted_banned_words()])


def _strip_ignored_regions(text: str) -> str:
    """Remove regions where banned phrases shouldn't be enforced.

    Code blocks and quoted strings are fair game — they're usually
    citing or discussing a phrase, not using it.
    """
    # Fenced code blocks
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # Inline code
    text = re.sub(r"`[^`\n]+`", " ", text)
    # Double-quoted strings (for discussing phrases)
    text = re.sub(r'"[^"\n]*"', " ", text)
    # Single-quoted when clearly a quote (not apostrophe)
    text = re.sub(r"(?<!\w)'[^'\n]*'(?!\w)", " ", text)
    return text


def check_text(text: str, *, ignore_code: bool = True) -> set[str] | None:
    """Find banned phrases in text using word-boundary, case-insensitive matching.

    Skips phrases inside code blocks and quoted strings by default, so Charlie
    can still discuss or quote banned phrases without tripping the hook.

    Returns a list of matched phrases or none if there aren't any
    """
    text = text.strip().lower()

    if not text:
        return None

    scan_text = _strip_ignored_regions(text) if ignore_code else text
    seen: set[str] = set()

    for phrase in BANNED_WORDS:
        # Word-boundary match, case-insensitive
        pattern = r"\b" + re.escape(phrase) + r"\b"
        match = re.search(pattern, scan_text)
        if match:
            seen.add(phrase)

    if seen:
        return seen


def format_feedback(matches: set[str]) -> str:
    """Format matches into a rephrase-friendly message for the hook."""

    return f"Rephrase without using: {', '.join([f'"{m}"' for m in matches])}"


if __name__ == "__main__":
    print(banned_word_string())
