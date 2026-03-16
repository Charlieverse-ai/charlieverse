"""FTS5 query utilities."""

from __future__ import annotations

import re

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "for",
    "from", "had", "has", "have", "he", "her", "him", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "just", "me", "my", "no",
    "not", "of", "on", "or", "our", "out", "so", "some", "than", "that",
    "the", "their", "them", "then", "there", "these", "they", "this",
    "to", "up", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "will", "with", "would", "you", "your",
    "about", "after", "again", "also", "back", "been", "before",
    "being", "between", "both", "came", "can", "come", "could",
    "did", "does", "each", "even", "get", "got", "here", "himself",
    "into", "its", "let", "like", "make", "many", "might", "more",
    "most", "much", "must", "now", "off", "only", "other", "over",
    "own", "really", "remember", "right", "said", "say", "she",
    "should", "since", "still", "such", "take", "tell", "thing",
    "think", "those", "through", "too", "under", "upon", "very",
    "want", "way", "well", "went", "while", "why", "yeah", "yes",
})


def sanitize_fts_query(raw: str) -> str:
    """Convert raw search input to a safe FTS5 query with prefix matching.

    Strips special characters, removes stopwords, tokenizes,
    and wraps each token with quotes + prefix wildcard.
    Uses OR joining so partial matches still return results.
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", raw)
    meaningful = [t for t in tokens if t.lower() not in _STOPWORDS and len(t) > 1]
    if not meaningful:
        return ""
    return " OR ".join(f'"{t}"*' for t in meaningful)
