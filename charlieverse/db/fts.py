"""FTS5 query utilities."""

from __future__ import annotations

from charlieverse.helpers.text import clean_text


def sanitize_fts_query(raw: str) -> str:
    """Convert raw search input to a safe FTS5 query with prefix matching.

    Strips special characters, removes stopwords, tokenizes, and wraps each
    token with quotes + prefix wildcard. Uses OR joining so partial matches
    still return results. Returns "" when no usable tokens remain — callers
    should check truthiness before issuing the query.
    """
    text = clean_text(raw)
    if not text:
        return ""

    # FTS5 wraps each token in double quotes to treat it as a phrase. The
    # embedded token can't contain an unescaped quote or the parser blows up
    # with "unterminated string". Strip any stray quotes from each token and
    # drop tokens that evaporate entirely.
    tokens = [t.replace('"', "") for t in text.split(" ")]
    tokens = [t for t in tokens if len(t) > 1]
    if not tokens:
        return ""

    return " OR ".join(f'"{t}"*' for t in tokens)
