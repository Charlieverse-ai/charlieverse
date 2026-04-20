from __future__ import annotations

import re
from string import punctuation

from charlieverse.types.strings import CleanedText

_shared_punctuation_translator = str.maketrans("", "", punctuation)


def normalize_whitespace(text: str) -> str:
    return "\n".join([line.strip() for line in text.splitlines()])


def strip_punctuation(text: str) -> str:
    return text.translate(_shared_punctuation_translator)


def strip_markdown(text: str) -> str:
    """Remove common markdown formatting and return plain text.

    Handles: headers, bold/italic, code fences, inline code, links,
    images, bullet/numbered lists, horizontal rules, blockquotes,
    and collapses excessive whitespace.
    """
    if not text:
        return text

    s = normalize_whitespace(text)

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


def is_ignored(text: str) -> bool:
    if text.startswith("[Request interrupted"):
        return True

    # Slash commands
    if re.match(r"^\/([\w-]+)(?:\s+(.*))?$", text):
        return True

    # XML tag messages: `<task-notification>...</task-notification>`
    return bool(re.match(r"<\s*([\w-]+)[^>]*>([\s\S]*?)<\s*\/\s*\1\s*>", text))


def strip_noise(content: str) -> str:
    """Remove file paths, URLs, code blocks, and multiple spaces"""
    # Strip URLs
    content = re.sub(r"https?://\S+", " ", content, flags=re.MULTILINE)
    # snake_case
    content = re.sub(r"\b[a-z]+(?:_[a-z]+)+\b", " ", content)
    # kebab-case
    content = re.sub(r"\b[a-z]+(?:-[a-z]+)+\b", " ", content)
    # camelCase
    content = re.sub(r"\b[a-z]+[A-Z]\w*\b", " ", content)
    # PascalCase
    content = re.sub(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", " ", content)
    # Strip file paths (absolute and relative)
    content = re.sub(r'(\/.*|[a-zA-Z]:\\(?:([^<>:"\/\\|?*]*[^<>:"\/\\|?*.]\\|..\\)*([^<>:"\/\\|?*]*[^<>:"\/\\|?*.]\\?|..\\))?)', " ", content)
    # Strip git log lines (e.g. "abc1234 Charlie Mar 5 ...")
    content = re.sub(r"^[a-f0-9]{6,}\s+.*$", " ", content, flags=re.MULTILINE)
    # Strip lines that look like shell output / file listings
    content = re.sub(r"^[\-drwx]{10}\s+.*$", " ", content, flags=re.MULTILINE)
    # ```code blocks```
    content = re.sub(r"```[a-z]*(\n)?[\s\S]*?\n?```$", " ", content, flags=re.MULTILINE)
    # Inline `code`
    content = re.sub(r"(?<!`)(`)([^`]+)\1(?!`)", " ", content, flags=re.MULTILINE)
    # Strip all multi dashes (-----)
    content = re.sub(r"-{2,}", " ", content)
    # Strip UUIDs
    content = re.sub(r"[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}", " ", content)
    # Collapse the whitespace runs left behind by all the substitutions above,
    # so downstream phrase-matching sees "a few things" and not "a  few  things".
    content = re.sub(r"[ \t]{2,}", " ", content)

    return content.strip()


def extract_stuff(content: str) -> list[str]:
    return list(
        set(
            re.findall(
                r"(~?(?:\/[\w.-]+){2,}\/?|https?://\S+|\b[a-z]{3,}(?:_[a-z]+)+\b|\b[a-z]{3,}(?:-[a-z]{3,})+\b|\b[a-z]{3,}[A-Z]\w*\b|\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b|\b[A-Z][a-z]{3,}\b)",
                content,
            )
        )
    )


def clean_stopwords(tokens: list[str]) -> list[str]:
    from charlieverse.helpers.stop_words import STOP_WORDS

    return [t for t in tokens if t.lower() not in STOP_WORDS and len(t) > 3]


def clean_text(text: str | CleanedText | None) -> CleanedText | None:
    if not text:
        return None

    if isinstance(text, CleanedText):
        return text

    # Strip null bytes and other control chars that break SQLite FTS5.
    string = text.replace("\x00", "").strip()
    if not string or is_ignored(string):
        return None

    string = strip_noise(string)
    if not string:
        return None

    # Normalize multiple spaces to 1
    string = re.sub(r"\s{2,}", " ", string, flags=re.MULTILINE)

    tokens = string.lower().split(" ")
    filtered = clean_stopwords(tokens)
    if not filtered:
        return None

    return CleanedText.or_none(" ".join(filtered))
