"""Tests for EntityType — workspace scoping rules for all entity types."""

from __future__ import annotations

import pytest

from charlieverse.models.entity import EntityType


# ---------------------------------------------------------------------------
# Workspace-scoped types (technical)
# ---------------------------------------------------------------------------


def test_decision_is_workspace_scoped():
    assert EntityType.decision.is_workspace_scoped is True


def test_solution_is_workspace_scoped():
    assert EntityType.solution.is_workspace_scoped is True


def test_milestone_is_workspace_scoped():
    assert EntityType.milestone.is_workspace_scoped is True


def test_project_is_workspace_scoped():
    assert EntityType.project.is_workspace_scoped is True


# ---------------------------------------------------------------------------
# Global types (personality / personal)
# ---------------------------------------------------------------------------


def test_moment_is_global():
    assert EntityType.moment.is_workspace_scoped is False


def test_preference_is_global():
    assert EntityType.preference.is_workspace_scoped is False


def test_person_is_global():
    assert EntityType.person.is_workspace_scoped is False


def test_event_is_global():
    assert EntityType.event.is_workspace_scoped is False


# ---------------------------------------------------------------------------
# Exhaustive: every type has a defined scoping
# ---------------------------------------------------------------------------


def test_all_types_have_defined_scoping():
    """Every EntityType must return True or False — no unhandled match arm."""
    for entity_type in EntityType:
        result = entity_type.is_workspace_scoped
        assert isinstance(result, bool), f"{entity_type} returned non-bool: {result!r}"


# ---------------------------------------------------------------------------
# String values
# ---------------------------------------------------------------------------


def test_project_str_value():
    assert EntityType.project == "project"


def test_event_str_value():
    assert EntityType.event == "event"
