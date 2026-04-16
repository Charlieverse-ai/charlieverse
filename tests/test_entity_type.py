"""Tests for EntityType — string values and enum completeness."""

from __future__ import annotations

from charlieverse.memory.entities import EntityType

# ---------------------------------------------------------------------------
# String values
# ---------------------------------------------------------------------------


def test_project_str_value():
    assert EntityType.project == "project"


def test_event_str_value():
    assert EntityType.event == "event"


def test_all_types_are_strings():
    """Every EntityType must have a string value."""
    for entity_type in EntityType:
        assert isinstance(entity_type.value, str), f"{entity_type} has non-string value"
