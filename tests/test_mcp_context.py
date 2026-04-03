"""Tests for charlieverse/mcp/context.py helpers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from charlieverse.mcp.context import _permalink, _remember_with_url

# ---------------------------------------------------------------------------
# _permalink
# ---------------------------------------------------------------------------


def test_permalink_includes_kind_and_id():
    result = _permalink("memories", "abc123")
    assert "memories" in result
    assert "abc123" in result


def test_permalink_returns_string():
    result = _permalink("knowledge", "def456")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _remember_with_url — returns url only, no id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remember_with_url_returns_url():
    """_remember_with_url should return a dict with a 'url' key."""

    class FakeResult:
        id = uuid4()

    result = await _remember_with_url(FakeResult())
    assert "url" in result


@pytest.mark.asyncio
async def test_remember_with_url_does_not_return_id():
    """After the refactor, 'id' must NOT be in the returned dict."""

    class FakeResult:
        id = uuid4()

    result = await _remember_with_url(FakeResult())
    assert "id" not in result


@pytest.mark.asyncio
async def test_remember_with_url_url_contains_id():
    """The URL should embed the entity ID."""
    entity_id = uuid4()

    class FakeResult:
        id = entity_id

    result = await _remember_with_url(FakeResult())
    assert str(entity_id) in result["url"]


@pytest.mark.asyncio
async def test_remember_with_url_custom_kind():
    """Custom kind should be reflected in the URL."""
    entity_id = uuid4()

    class FakeResult:
        id = entity_id

    result = await _remember_with_url(FakeResult(), kind="knowledge")
    assert "knowledge" in result["url"]
