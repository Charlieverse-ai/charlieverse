"""Tests for PermalinkResponse — locks the structured_content contract.

The MCP write-tools (update_session, save_memory, save_story, update_article,
forget_memory, pin) all return PermalinkResponse. FastMCP auto-generates an
outputSchema from the return type annotation, and MCP clients (Claude Code in
particular) reject responses that have a declared outputSchema but no
structured_content. PermalinkResponse must always set structured_content to a
non-None dict so the validator passes and the writes don't appear to error.

Bug fixed April 25 2026 (logged in BACKLOG.md as "MCP write-tools throw
output-validation errors despite writes landing"). These tests prevent
regression.
"""

from __future__ import annotations

import pytest
from mcp.types import TextContent

from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.types.id import ModelId

_FIXED_ID = ModelId("550e8400-e29b-41d4-a716-446655440000")


def test_permalink_response_sets_structured_content() -> None:
    """The MCP outputSchema validator requires structured_content to be a dict, not None."""
    result = PermalinkResponse("sessions", _FIXED_ID)
    assert result.structured_content is not None
    assert isinstance(result.structured_content, dict)


def test_permalink_response_structured_content_includes_kind_id_url() -> None:
    """Clients should be able to read the kind, id, and url from the structured payload."""
    result = PermalinkResponse("memories", _FIXED_ID)
    sc = result.structured_content
    assert sc is not None
    assert sc["kind"] == "memories"
    assert sc["id"] == str(_FIXED_ID)
    assert "url" in sc
    assert sc["url"].endswith(f"memories/{_FIXED_ID}")


def test_permalink_response_text_content_matches_url() -> None:
    """The TextContent block should carry the same URL as the structured payload."""
    result = PermalinkResponse("story", _FIXED_ID)
    assert result.content is not None
    assert len(result.content) == 1
    text_block = result.content[0]
    assert isinstance(text_block, TextContent)
    sc = result.structured_content
    assert sc is not None
    assert text_block.text == sc["url"]


@pytest.mark.parametrize(
    "kind",
    ["sessions", "memories", "knowledge", "story"],
)
def test_permalink_response_supports_all_write_tool_kinds(kind: str) -> None:
    """Every kind the MCP write-tools emit should produce a valid PermalinkResponse."""
    result = PermalinkResponse(kind, _FIXED_ID)
    assert result.structured_content is not None
    assert result.structured_content["kind"] == kind
