"""Shared fixtures for the Charlieverse test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from charlieverse.db import database
from charlieverse.db.stores import (
    KnowledgeStore,
    MemoryStore,
    SessionStore,
    StoryStore,
)
from charlieverse.embeddings import EMBEDDING_DIM


@pytest_asyncio.fixture
async def db():
    """Fresh in-memory database with all migrations applied."""
    conn = await database.connect(":memory:")
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def memory_store(db):
    """MemoryStore backed by the shared in-memory database."""
    return MemoryStore(db)


@pytest_asyncio.fixture
async def knowledge_store(db):
    """KnowledgeStore backed by the shared in-memory database."""
    return KnowledgeStore(db)


@pytest_asyncio.fixture
async def story_store(db):
    """StoryStore backed by the shared in-memory database."""
    return StoryStore(db)


@pytest_asyncio.fixture
async def session_store(db):
    """SessionStore backed by the shared in-memory database."""
    return SessionStore(db)


@pytest.fixture
def mock_embed():
    """Patch encode_one to return a list of 384 zeros (no model load, no I/O).

    Patches both the public module symbol and the direct import used by the
    background embedding task so neither path ever loads the model.
    """
    zero_vec = [0.0] * EMBEDDING_DIM
    with (
        patch(
            "charlieverse.embeddings.encode_one",
            new=AsyncMock(return_value=zero_vec),
        ),
        patch(
            "charlieverse.embeddings.tasks.encode_one",
            new=AsyncMock(return_value=zero_vec),
        ) as m,
    ):
        yield m
