"""Tests for PermalinkResponse — locks the contract used by MCP write-tools.

The MCP write-tools (update_session, save_memory, save_story, update_article,
forget_memory, pin) all return PermalinkResponse. PermalinkResponse must be a
plain Pydantic model — NOT a fastmcp ToolResult subclass — so FastMCP can
derive an outputSchema describing just the structured payload (kind, id, url).

When PermalinkResponse extended ToolResult, the auto-generated outputSchema
leaked transport-envelope fields (content / structured_content / meta) and
clients rejected responses where those fields were missing or shaped wrong.
That bug fired on every save_memory and update_session call during the
April 24-25 Fiona deliverable session saves. These tests prevent regression.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from charlieverse.server.responses.permalink import PermalinkResponse
from charlieverse.types.id import ModelId

_FIXED_ID = ModelId("550e8400-e29b-41d4-a716-446655440000")


def test_permalink_response_is_a_plain_pydantic_model() -> None:
    """PermalinkResponse must NOT extend ToolResult — that leaks envelope fields into the schema."""
    from fastmcp.tools import ToolResult

    assert issubclass(PermalinkResponse, BaseModel)
    assert not issubclass(PermalinkResponse, ToolResult)


def test_permalink_response_positional_constructor_for_back_compat() -> None:
    """Existing call sites use PermalinkResponse(kind, id) — preserve that shape."""
    result = PermalinkResponse("sessions", _FIXED_ID)
    assert result.kind == "sessions"
    assert result.id == str(_FIXED_ID)
    assert result.url.endswith(f"sessions/{_FIXED_ID}")


def test_permalink_response_for_entity_classmethod() -> None:
    """Explicit factory method for callers that prefer named args."""
    result = PermalinkResponse.for_entity("memories", _FIXED_ID)
    assert result.kind == "memories"
    assert result.id == str(_FIXED_ID)
    assert result.url.endswith(f"memories/{_FIXED_ID}")


def test_permalink_response_dumps_to_dict_with_kind_id_url() -> None:
    """The model_dump payload is what FastMCP sends as structured_content."""
    result = PermalinkResponse("knowledge", _FIXED_ID)
    payload = result.model_dump()
    assert set(payload.keys()) == {"kind", "id", "url"}
    assert payload["kind"] == "knowledge"
    assert payload["id"] == str(_FIXED_ID)


@pytest.mark.parametrize(
    "kind",
    ["sessions", "memories", "knowledge", "story"],
)
def test_permalink_response_supports_all_write_tool_kinds(kind: str) -> None:
    """Every kind the MCP write-tools emit should produce a valid PermalinkResponse."""
    result = PermalinkResponse(kind, _FIXED_ID)
    assert result.kind == kind
    assert result.url.startswith("http")
    assert result.url.endswith(f"{kind}/{_FIXED_ID}")
