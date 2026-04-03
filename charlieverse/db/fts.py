"""FTS5 query utilities."""

from __future__ import annotations

import re

from spacy.lang.en.stop_words import STOP_WORDS


def sanitize_fts_query(raw: str) -> str:
    """Convert raw search input to a safe FTS5 query with prefix matching.

    Strips special characters, removes stopwords, tokenizes,
    and wraps each token with quotes + prefix wildcard.
    Uses OR joining so partial matches still return results.
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", raw)
    meaningful = [t for t in tokens if t.lower() not in STOP_WORDS and len(t) > 1]
    if not meaningful:
        return ""
    return " OR ".join(f'"{t}"*' for t in meaningful)
