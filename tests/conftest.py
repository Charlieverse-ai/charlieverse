"""Shared fixtures for the Charlieverse test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from charlieverse.db import database
from charlieverse.embeddings import EMBEDDING_DIM
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.messages.store import MessageStore
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stores import Stores
from charlieverse.memory.stories import StoryStore


@pytest_asyncio.fixture
async def db():
    """Fresh in-memory database with all migrations applied."""
    conn = await database.connect(":memory:")
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def memory_store(db):
    """EntityStore backed by the shared in-memory database."""
    return EntityStore(db)


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


@pytest_asyncio.fixture
async def message_store(db):
    """MessageStore backed by the shared in-memory database."""
    return MessageStore(db)


@pytest_asyncio.fixture
async def stores(memory_store, knowledge_store, session_store, story_store, message_store):
    """Stores aggregate backed by the shared in-memory database."""
    return Stores(
        memories=memory_store,
        knowledge=knowledge_store,
        sessions=session_store,
        stories=story_store,
        messages=message_store,
    )


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
