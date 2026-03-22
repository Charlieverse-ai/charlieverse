"""Tests for the activation context renderer (charlieverse/context/renderer.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from charlieverse.context.builder import ContextBundle
from charlieverse.context.renderer import render, _render_entity, _date_group_key, _session_time
from charlieverse.models import Entity, EntityType, Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(
    what_happened: str = "worked on things",
    for_next_session: str | None = None,
    workspace: str | None = None,
    updated_at: datetime | None = None,
) -> Session:
    s = Session(
        what_happened=what_happened,
        for_next_session=for_next_session,
        workspace=workspace,
    )
    if updated_at:
        s = s.model_copy(update={"updated_at": updated_at})
    return s


def _entity(
    content: str = "test content",
    type: EntityType = EntityType.decision,
    updated_at: datetime | None = None,
) -> Entity:
    e = Entity(
        type=type,
        content=content,
        created_session_id=uuid4(),
    )
    if updated_at:
        e = e.model_copy(update={"updated_at": updated_at})
    return e


def _bundle(**kwargs) -> ContextBundle:
    """Build a minimal ContextBundle. Must have a non-first-run configuration."""
    base_session = _session()
    # Provide at least one moment so is_first_run is False.
    moments = kwargs.pop("moments", [_entity("personality moment", type=EntityType.moment)])
    return ContextBundle(session=base_session, moments=moments, **kwargs)


# ---------------------------------------------------------------------------
# Session tag structure
# ---------------------------------------------------------------------------


def test_most_recent_session_wrapped_in_last_session_tag():
    now = datetime.now(timezone.utc)
    recent = _session("most recent work", updated_at=now - timedelta(minutes=5))
    older = _session("older work", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[recent, older])
    output = render(bundle)
    assert "<last_session>" in output
    assert "</last_session>" in output


def test_non_recent_sessions_wrapped_in_session_tag():
    now = datetime.now(timezone.utc)
    recent = _session("most recent", updated_at=now - timedelta(minutes=5))
    older = _session("older session", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[recent, older])
    output = render(bundle)
    assert "<session>" in output
    assert "</session>" in output


def test_only_first_session_gets_last_session_tag():
    now = datetime.now(timezone.utc)
    s1 = _session("first", updated_at=now - timedelta(minutes=5))
    s2 = _session("second", updated_at=now - timedelta(hours=1))
    s3 = _session("third", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[s1, s2, s3])
    output = render(bundle)
    assert output.count("<last_session>") == 1
    assert output.count("</last_session>") == 1
    # Two non-recent sessions
    assert output.count("<session>") == 2


def test_no_our_timeline_wrapper():
    now = datetime.now(timezone.utc)
    recent = _session("some work", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = render(bundle)
    assert "<our_timeline>" not in output
    assert "</our_timeline>" not in output


def test_single_session_uses_last_session_tag():
    now = datetime.now(timezone.utc)
    only = _session("only session", updated_at=now - timedelta(minutes=10))
    bundle = _bundle(recent_sessions=[only])
    output = render(bundle)
    assert "<last_session>" in output
    assert "<session>" not in output


# ---------------------------------------------------------------------------
# Temporal weighting note
# ---------------------------------------------------------------------------


def test_time_weighting_note_present():
    bundle = _bundle()
    output = render(bundle)
    assert "Weight information according to relative time" in output


def test_sessions_ordering_note_present_when_sessions_exist():
    now = datetime.now(timezone.utc)
    recent = _session("recent", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = render(bundle)
    assert "Sessions are ordered from most recent to least" in output


# ---------------------------------------------------------------------------
# _render_entity — moment formatting
# ---------------------------------------------------------------------------


def test_moment_entity_renders_with_bullet_date():
    moment = _entity("a memory moment", type=EntityType.moment)
    output = _render_entity(moment)
    # Should start with "- " (bullet list item)
    lines = output.strip().splitlines()
    assert lines[0].startswith("- ")


def test_moment_entity_does_not_use_saved_prefix():
    moment = _entity("another moment", type=EntityType.moment)
    output = _render_entity(moment)
    assert "Saved:" not in output


def test_non_moment_entity_renders_type_header():
    entity = _entity("a decision", type=EntityType.decision)
    output = _render_entity(entity)
    assert "## Decision" in output


def test_non_moment_entity_date_header_has_no_saved_prefix():
    entity = _entity("some preference", type=EntityType.preference)
    output = _render_entity(entity)
    assert "Saved:" not in output
    # Date line should start with "### " but NOT "### Saved:"
    lines = output.strip().splitlines()
    date_lines = [l for l in lines if l.startswith("### ")]
    assert len(date_lines) == 1
    assert not date_lines[0].startswith("### Saved:")


# ---------------------------------------------------------------------------
# very-important tag (was <important>)
# ---------------------------------------------------------------------------


def test_very_important_tag_used_not_important():
    bundle = _bundle()
    output = render(bundle)
    # The old tag should not appear; the new one should
    assert "<important>" not in output
    assert "<very-important>" in output


# ---------------------------------------------------------------------------
# _date_group_key
# ---------------------------------------------------------------------------


def test_date_group_key_today():
    now = datetime.now().astimezone()
    assert _date_group_key(now, now) == "Today"


def test_date_group_key_yesterday():
    now = datetime.now().astimezone()
    yesterday = now - timedelta(days=1)
    result = _date_group_key(yesterday, now)
    assert result.startswith("Yesterday")


def test_date_group_key_older():
    now = datetime.now().astimezone()
    older = now - timedelta(days=5)
    result = _date_group_key(older, now)
    # Should be a full date string, not Today/Yesterday
    assert result not in ("Today", ) and not result.startswith("Yesterday")


# ---------------------------------------------------------------------------
# _session_time
# ---------------------------------------------------------------------------


def test_session_time_just_now():
    now = datetime.now().astimezone()
    result = _session_time(now - timedelta(seconds=10), now)
    assert "just now" in result


def test_session_time_minutes_ago():
    now = datetime.now().astimezone()
    result = _session_time(now - timedelta(minutes=30), now)
    assert "minutes ago" in result


def test_session_time_hours_ago():
    now = datetime.now().astimezone()
    result = _session_time(now - timedelta(hours=3), now)
    assert "hours ago" in result


def test_session_time_yesterday_returns_time_only():
    now = datetime.now().astimezone()
    yesterday = now - timedelta(days=1)
    result = _session_time(yesterday, now)
    # Should not include "ago" — just a time string
    assert "ago" not in result
