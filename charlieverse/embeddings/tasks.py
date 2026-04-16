"""Background embedding tasks — fire-and-forget helpers for tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from charlieverse.embeddings.service import encode_one

if TYPE_CHECKING:
    pass


async def fire_and_forget_embedding(
    text: str,
    upsert_fn: Callable[[list[float]], Awaitable[Any]],
) -> None:
    """Generate an embedding and persist it. Best-effort — never raises.

    Args:
        text: The text to encode.
        upsert_fn: Async callable that receives the embedding and stores it.
    """
    try:
        embedding = await encode_one(text)
        await upsert_fn(embedding)
    except Exception:
        pass
