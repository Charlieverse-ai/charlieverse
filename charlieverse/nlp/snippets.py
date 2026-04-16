"""Smart snippet extraction — finds the most relevant section of a document."""

from __future__ import annotations

import numpy as np


def extract_snippet(
    content: str,
    query_embedding: list[float],
    context_paragraphs: int = 1,
    max_chars: int = 500,
) -> str:
    """Find the most relevant paragraphs in content relative to a query.

    Splits content into paragraphs, embeds each, finds the one closest
    to query_embedding via cosine similarity, then returns it with
    surrounding context paragraphs.

    Args:
        content: Full text to extract from.
        query_embedding: Pre-computed embedding of the search query.
        context_paragraphs: Number of paragraphs before/after the best match to include.
        max_chars: Maximum length of the returned snippet.

    Returns:
        The most relevant section of the content.
    """
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    if not paragraphs:
        return content[:max_chars]

    if len(paragraphs) <= 3:
        return content[:max_chars]

    # Embed all paragraphs in one batch
    from charlieverse.embeddings.service import _get_model

    model = _get_model()
    para_embeddings = model.encode(paragraphs, show_progress_bar=False)

    # Cosine similarity between query and each paragraph
    query_vec = np.array(query_embedding)
    scores = []
    for emb in para_embeddings:
        para_vec = np.array(emb)
        cos_sim = np.dot(query_vec, para_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(para_vec) + 1e-8)
        scores.append(cos_sim)

    best_idx = int(np.argmax(scores))

    # Grab surrounding context
    start = max(0, best_idx - context_paragraphs)
    end = min(len(paragraphs), best_idx + context_paragraphs + 1)

    snippet = "\n\n".join(paragraphs[start:end])

    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0] + "..."

    return snippet
