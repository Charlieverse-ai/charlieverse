"""Embedding service — generates vector embeddings for semantic search."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Single-worker executor — the model is not thread-safe for concurrent encoding
_executor = ThreadPoolExecutor(max_workers=1)
_model: SentenceTransformer | None = None


def prewarm_embeddings():
    _get_model()


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME, device="cpu", local_files_only=True)

    return _model


async def encode(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Runs the model in a thread pool to avoid blocking the event loop.
    Returns a list of float vectors (384 dimensions each).
    """
    loop = asyncio.get_running_loop()
    embeddings = await loop.run_in_executor(
        _executor,
        lambda: _get_model().encode(texts).tolist(),
    )
    return embeddings


async def encode_one(text: str) -> list[float]:
    """Generate an embedding for a single text."""
    results = await encode([text])
    return results[0]


def prepare_entity_text(content: str, tags: list[str] | None = None) -> str:
    """Prepare entity text for embedding generation."""
    parts = [content]
    if tags:
        parts.append(" ".join(tags))
    return " ".join(parts)


def prepare_knowledge_text(topic: str, content: str, tags: list[str] | None = None) -> str:
    """Prepare knowledge text for embedding generation."""
    parts = [topic, content]
    if tags:
        parts.append(" ".join(tags))
    return " ".join(parts)


def prepare_session_text(
    what_happened: str | None = None,
    for_next_session: str | None = None,
) -> str:
    """Prepare session text for embedding generation."""
    parts: list[str] = []
    if what_happened:
        parts.append(what_happened)
    if for_next_session:
        parts.append(for_next_session)
    return " ".join(parts) if parts else ""
