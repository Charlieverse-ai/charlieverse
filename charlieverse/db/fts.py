"""FTS5 query utilities."""

from __future__ import annotations

import re

from charlieverse.helpers.stop_words import STOP_WORDS


def is_ignored(text: str) -> bool:
    # Slash commands
    if re.match(r"^\/([\w-]+)(?:\s+(.*))?$", text):
        return True

    # XML tag messages: `<task-notification>...</task-notification>`
    return bool(re.match(r"<\s*([\w-]+)[^>]*>([\s\S]*?)<\s*\/\s*\1\s*>", text))


def strip_noise(content: str) -> str:
    """Remove file paths, URLs, code blocks, and multiple  spaces"""
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
    content = re.sub(r'([a-zA-Z]:\\|\/)[^"<>|]+?[^"<>|]*\.\w+', " ", content)
    # Strip git log lines (e.g. "abc1234 Charlie Mar 5 ...")
    content = re.sub(r"^[a-f0-9]{6,}\s+.*$", " ", content, flags=re.MULTILINE)
    # Strip lines that look like shell output / file listings
    content = re.sub(r"^[\-drwx]{10}\s+.*$", " ", content, flags=re.MULTILINE)
    # ```code blocks```
    content = re.sub(r"```[a-z]*(\n)?[\s\S]*?\n?```$", " ", content, flags=re.MULTILINE)
    # Inline `code`
    content = re.sub(r"(?<!`)(`)([^`]+)\1(?!`)", " ", content, flags=re.MULTILINE)
    # Normalize all multi spaces to 1
    content = re.sub(r"\s{2,}", " ", content, flags=re.MULTILINE)

    return content.strip()


def clean_text(text: str) -> str | None:
    string = text.strip()
    if not string or is_ignored(string):
        return None

    string = strip_noise(string)
    if not string:
        return None

    tokens = re.findall(r"[\w-]+", string.lower())
    filtered = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    if filtered:
        return " ".join(filtered)


def sanitize_fts_query(raw: str) -> str | None:
    """Convert raw search input to a safe FTS5 query with prefix matching.

    Strips special characters, removes stopwords, tokenizes,
    and wraps each token with quotes + prefix wildcard.
    Uses OR joining so partial matches still return results.
    """
    text = clean_text(raw)
    if not text:
        return None

    query = " OR ".join(f'"{t}"*' for t in text.split(" "))
    return query
