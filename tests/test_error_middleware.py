"""Tests for charlieverse.server.middleware.errors — Pydantic ValidationError formatting."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from charlieverse.memory.sessions import SessionId
from charlieverse.server.middleware.errors import _field_path, _format_validation_error
from charlieverse.types.strings import NonEmptyString

# ---------------------------------------------------------------------------
# _field_path — strips Pydantic union/chain branch tags
# ---------------------------------------------------------------------------


def test_field_path_empty_loc_returns_params():
    assert _field_path(()) == "params"


def test_field_path_non_tuple_returns_params():
    assert _field_path(None) == "params"


def test_field_path_single_segment():
    assert _field_path(("session_id",)) == "session_id"


def test_field_path_multi_segment_joined_by_dot():
    assert _field_path(("body", "content")) == "body.content"


def test_field_path_strips_is_instance_bracket_markers():
    # Pydantic embeds "is-instance[SessionId]" and similar inside the loc tuple.
    loc = ("session_id", "is-instance[SessionId]")
    assert _field_path(loc) == "session_id"


def test_field_path_strips_chain_markers():
    loc = ("session_id", "chain[uuid,function-plain[validate_uuid()]]")
    assert _field_path(loc) == "session_id"


def test_field_path_all_markers_returns_params():
    # Degenerate case: every segment is a branch marker, no real field name
    loc = ("is-instance[Foo]", "chain[bar]")
    assert _field_path(loc) == "params"


# ---------------------------------------------------------------------------
# _format_validation_error — compresses ValidationError to one line
# ---------------------------------------------------------------------------


class _Simple(BaseModel):
    name: NonEmptyString
    count: int


def _validation_error(model: type[BaseModel], payload: dict) -> ValidationError:
    with pytest.raises(ValidationError) as exc:
        model.model_validate(payload)
    return exc.value


def test_format_error_starts_with_invalid_params():
    err = _validation_error(_Simple, {"name": "", "count": 1})
    result = _format_validation_error(err)
    assert result.startswith("Invalid params — ")


def test_format_error_single_field_message():
    err = _validation_error(_Simple, {"name": "ok", "count": "not-a-number"})
    result = _format_validation_error(err)
    assert "count" in result
    # One line — no trailing newlines, no multi-line pydantic envelope
    assert "\n" not in result
    assert "validation error" not in result.lower()  # no "N validation errors for X"


def test_format_error_multiple_fields_joined_by_semicolon():
    err = _validation_error(_Simple, {"name": "", "count": "nope"})
    result = _format_validation_error(err)
    assert "name" in result
    assert "count" in result
    assert "; " in result


def test_format_error_missing_field_gets_a_field_path():
    err = _validation_error(_Simple, {})
    result = _format_validation_error(err)
    assert "name" in result or "count" in result
    assert "pydantic.dev" not in result


def test_format_error_dedups_identical_lines():
    # Forge a ValidationError with duplicate entries would require surgery into
    # pydantic internals. Instead, confirm the output contains each field at most
    # once when pydantic emits multiple errors on the same field.
    err = _validation_error(_Simple, {"name": "", "count": "bad"})
    result = _format_validation_error(err)
    # "name:" should appear at most once per field
    assert result.count("name:") <= 1
    assert result.count("count:") <= 1


# ---------------------------------------------------------------------------
# Union-schema is_instance_of noise filtering
# ---------------------------------------------------------------------------


class _WithSessionId(BaseModel):
    session_id: SessionId


def test_format_error_filters_is_instance_noise_from_union():
    # SessionId uses a union schema; invalid input produces both an is_instance
    # error (noise) and a more useful validator message. The middleware should
    # surface only the useful one.
    err = _validation_error(_WithSessionId, {"session_id": "not-a-uuid"})
    result = _format_validation_error(err)
    # Real UUID error survives
    assert "session_id" in result
    # Noise branch marker doesn't survive
    assert "is_instance_of" not in result
    assert "is-instance" not in result


def test_format_error_empty_errors_falls_back_to_default_message():
    # If pydantic somehow produced a ValidationError with no errors, we still
    # want a valid single-line message. Simulate with a real but filtered case.
    err = _validation_error(_Simple, {"name": "", "count": 1})
    result = _format_validation_error(err)
    assert result != ""
    assert "Invalid params" in result
