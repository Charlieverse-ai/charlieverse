"""Banned Words that Charlie can't say"""

from __future__ import annotations

import re
from pathlib import Path

from charlieverse.helpers.text import strip_markdown, strip_noise, strip_punctuation
from charlieverse.types.strings import CleanedText

BANNED_WORDS = {
    "a few things",
    "absolutely right",
    "all the information",
    "audit trail",
    "based on my",
    "best practices",
    "canonical",
    "comprehensive",
    "conduct a thorough",
    "executive summary",
    "hard to believe",
    "help you",
    "here is a summary",
    "I can see",
    "i lean toward",
    "is a summary of",
    "key files",
    "knock these out",
    "make sure everything",
    "makes total sense",
    "might have missed",
    "my gut says",
    "my gut",
    "north star",
    "now i have",
    "quick sanity check",
    "root cause",
    "safety net",
    "say the word",
    "social proof",
    "source of truth",
    "start by",
    "systematically",
    "take your time",
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
}


# Syntactic patterns that can't be expressed as fixed phrases. Each entry is
# (label, regex). The label is what gets reported back to Charlie — make it
# describe the shape so he knows what he did, not just what he said.
BANNED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "'not just X, Y' escalation pattern",
        re.compile(
            r"\b(?:"
            r"did(?:n['\u2019]?t|\s+not)|"
            r"was(?:n['\u2019]?t|\s+not)|"
            r"were(?:n['\u2019]?t|\s+not)|"
            r"is(?:n['\u2019]?t|\s+not)|"
            r"are(?:n['\u2019]?t|\s+not)|"
            r"do(?:n['\u2019]?t|\s+not)|"
            r"does(?:n['\u2019]?t|\s+not)|"
            r"have(?:n['\u2019]?t|\s+not)|"
            r"has(?:n['\u2019]?t|\s+not)|"
            r"had(?:n['\u2019]?t|\s+not)|"
            r"can(?:n['\u2019]?ot|['\u2019]?t|\s+not)|"
            r"could(?:n['\u2019]?t|\s+not)|"
            r"will(?:\s+not)|won['\u2019]?t|"
            r"would(?:n['\u2019]?t|\s+not)|"
            r"ain['\u2019]?t|"
            r"not"
            r")\s+(?:just|only|merely|simply)\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'more than just X' elevation pattern",
        re.compile(
            r"\bmore\s+than\s+(?:just|merely|only|simply)\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'not so much X as Y' contrast-elevation pattern",
        re.compile(
            r"\bnot\s+so\s+much\s+.+?\s+as\s+",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'let me X' narration",
        # "let me check / look / try / verify / explore / read / continue / ..."
        # — the whole family of self-narrating lookup verbs.
        re.compile(r"\blet me\s+[a-z]+\b", flags=re.IGNORECASE),
    ),
    (
        "'the real/true/actual X' intensifier",
        # "the real issue", "the true purpose", "the actual source"
        re.compile(r"\bthe\s+(?:real|true|actual)\s+[a-z]+\b", flags=re.IGNORECASE),
    ),
    (
        "'the full X' completeness brag",
        # "the full picture", "got the full story", "the full context"
        re.compile(
            r"\bthe\s+full\s+(?:picture|story|context|scope|thing|deal|details|breakdown)\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'X clearly' rhetorical certainty",
        # "see the issue clearly", "understand it clearly", "know that clearly"
        re.compile(
            r"\b(?:see|saw|seeing|understand|understood|understanding|know|knew|knowing)"
            r"(?:\s+\w+){1,3}\s+clearly\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'classic X' idiom",
        # "classic Emily" (classic + capitalized name), "that's classic", "the classic".
        # Compiled without IGNORECASE so [A-Z] actually means uppercase
        # (needed to detect the capitalized-name form). Case flexibility on the
        # non-name parts is handled with [Cc]/[Tt] char classes.
        re.compile(
            r"\b[Cc]lassic\s+[A-Z][a-z]+\b|"
            r"\b[Tt]hat['\u2019]?s\s+[Cc]lassic\b|"
            r"\b[Tt]he\s+[Cc]lassic\b"
        ),
    ),
    (
        "any form of 'clean'",
        # Nuke the whole root. Emily hates it.
        # Covers: clean, cleans, cleaned, cleaning, cleanly, cleaner, cleaners,
        # cleanest, cleanup, cleanups.
        # Does NOT fire on: cleanse, cleanser, cleanliness (different root).
        re.compile(
            r"\bclean(?:s|ed|ing|ly|er|ers|est|up|ups)?\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "'or something else' trailing escape hatch",
        # Charlie lists options and ends with "or something else?" — a menu
        # with an escape hatch so he never has to commit to the menu being
        # complete, let alone pick an option. Pure deflection.
        re.compile(r"\bor\s+something\s+else\b", flags=re.IGNORECASE),
    ),
    (
        "'right to X' rhetorical entitlement",
        # "right to question", "right to be", "right to feel", "right to ask"
        re.compile(
            r"\bright\s+to\s+(?:question|be|have|feel|ask|know|expect|demand|say|complain|push|call|claim)\b",
            flags=re.IGNORECASE,
        ),
    ),
]


def sorted_banned_words() -> list[str]:
    words = list(BANNED_WORDS)
    words.sort()
    return words


def banned_word_string() -> str:
    return ", ".join([f'"{w}"' for w in sorted_banned_words()])


def _strip_ignored_regions(text: str) -> CleanedText | None:
    """Remove regions where banned phrases shouldn't be enforced.

    Code blocks and quoted strings are fair game — they're usually
    citing or discussing a phrase, not using it.
    """
    text = strip_noise(text)
    text = strip_markdown(text)

    # Double-quoted strings (for discussing phrases) — must come BEFORE strip_punctuation
    text = re.sub(r'"[^"\n]*"', " ", text)
    # Single-quoted when clearly a quote (not apostrophe)
    text = re.sub(r"(?<!\w)'[^'\n]*'(?!\w)", " ", text)

    text = strip_punctuation(text)

    return CleanedText.or_none(text)


def check_text(text: str | None) -> set[str] | None:
    """Find banned phrases in text using word-boundary, case-insensitive matching.

    Skips phrases inside code blocks and quoted strings, so Charlie can still
    discuss or quote banned phrases without tripping the hook.

    Returns a set of matched phrases, or None if there aren't any.
    """
    scan_text = _strip_ignored_regions(text) if text else None

    if not scan_text:
        return None

    seen: set[str] = set()

    for phrase in BANNED_WORDS:
        # Word-boundary match, case-insensitive
        pattern = r"\b" + re.escape(strip_punctuation(phrase)) + r"\b"
        match = re.search(pattern, scan_text, flags=re.IGNORECASE)
        if match:
            seen.add(phrase)

    for label, pattern in BANNED_PATTERNS:
        if pattern.search(scan_text):
            seen.add(label)

    if seen:
        return seen


def format_feedback(matches: set[str]) -> str:
    """Format matches as evidence for the hook — the template does the telling."""

    return f"Matched: {', '.join([f'"{m}"' for m in matches])}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) <= 1:
        print(banned_word_string())
        exit(0)

    path = Path(sys.argv[1])
    # Simple file check
    if path.exists():
        if path.is_dir():
            print("Path provided is a directory not a file")
            exit(2)
        result = check_text(path.read_text())
    else:
        result = check_text("\n".join(sys.argv[1:]))

    if result:
        print(format_feedback(result))
        exit(1)

    exit(0)
