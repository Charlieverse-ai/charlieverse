"""Tests for the activation context renderer (charlieverse/context/renderer.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from charlieverse.context.builder import ContextBundle
from charlieverse.context.renderer import (
    Renderer,
    _date_group_key,
    _parse_period_date,
    _render_entity,
    _render_recent_messages,
    _render_tricks,
    _session_time,
    render,
)
from charlieverse.memory.entities import Entity, EntityType
from charlieverse.memory.knowledge import Knowledge
from charlieverse.memory.messages import Message, MessageId, MessageRole
from charlieverse.memory.sessions import Session, SessionId
from charlieverse.memory.stories import Story
from charlieverse.types.dates import LocalDatetime, UTCDatetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(
    what_happened: str = "worked on things",
    for_next_session: str = "continue fixing bugs",
    workspace: str = "/workspace/path",
    updated_at: datetime | None = None,
) -> Session:
    from charlieverse.memory.sessions import SessionId

    now = updated_at or datetime.now(UTC)
    return Session.model_construct(
        id=SessionId(),
        what_happened=what_happened,
        for_next_session=for_next_session,
        workspace=workspace,
        tags=["tag"],
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _entity(
    content: str = "test content",
    type: EntityType = EntityType.decision,
    updated_at: datetime | None = None,
) -> Entity:
    from charlieverse.memory.entities import EntityId
    from charlieverse.memory.sessions import SessionId

    now = updated_at or datetime.now(UTC)
    return Entity.model_construct(
        id=EntityId(),
        type=type,
        content=content,
        tags=None,
        pinned=False,
        created_session_id=SessionId(),
        updated_session_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _bundle(**kwargs) -> ContextBundle:
    """Build a minimal ContextBundle. Must have a non-first-run configuration."""
    base_session = _session()
    # Provide at least one moment so is_first_run is False.
    moments = kwargs.pop("moments", [_entity("personality moment", type=EntityType.moment)])
    return ContextBundle(session=base_session, moments=moments, **kwargs)


# ---------------------------------------------------------------------------
# Session tag structure
# ---------------------------------------------------------------------------


def test_most_recent_session_has_most_recent_attr():
    now = datetime.now(UTC)
    recent = _session("most recent work", updated_at=now - timedelta(minutes=5))
    older = _session("older work", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[recent, older])
    output = render(bundle)
    assert 'most_recent="true"' in output
    assert "<session " in output
    assert "</session>" in output


def test_non_recent_sessions_wrapped_in_session_tag():
    now = datetime.now(UTC)
    recent = _session("most recent", updated_at=now - timedelta(minutes=5))
    older = _session("older session", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[recent, older])
    output = render(bundle)
    assert "<session " in output
    assert "</session>" in output


def test_only_first_session_gets_most_recent_attr():
    now = datetime.now(UTC)
    s1 = _session("first", updated_at=now - timedelta(minutes=5))
    s2 = _session("second", updated_at=now - timedelta(hours=1))
    s3 = _session("third", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[s1, s2, s3])
    output = render(bundle)
    assert output.count('most_recent="true"') == 1
    # All sessions use <session> tag
    assert output.count("<session ") == 3


def test_no_our_timeline_wrapper():
    now = datetime.now(UTC)
    recent = _session("some work", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = render(bundle)
    assert "<our_timeline>" not in output
    assert "</our_timeline>" not in output


def test_single_session_uses_session_tag():
    now = datetime.now(UTC)
    only = _session("only session", updated_at=now - timedelta(minutes=10))
    bundle = _bundle(recent_sessions=[only])
    output = render(bundle)
    assert "<session " in output
    assert 'most_recent="true"' in output


# ---------------------------------------------------------------------------
# Temporal weighting note
# ---------------------------------------------------------------------------


def test_time_weighting_note_present():
    bundle = _bundle()
    output = render(bundle)
    assert "Weight information according to relative time" in output


def test_sessions_wrapped_in_sessions_tag():
    now = datetime.now(UTC)
    recent = _session("recent", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = render(bundle)
    assert "<sessions>" in output
    assert "</sessions>" in output


# ---------------------------------------------------------------------------
# _render_entity — moment formatting
# ---------------------------------------------------------------------------


def test_moment_entity_renders_as_important_tag():
    moment = _entity("a memory moment", type=EntityType.moment)
    r = Renderer()
    _render_entity(moment, r)
    output = r.render()
    assert "<important-moment" in output
    assert "a memory moment" in output
    assert "</important-moment>" in output


def test_moment_entity_includes_date_attr():
    moment = _entity("another moment", type=EntityType.moment)
    r = Renderer()
    _render_entity(moment, r)
    output = r.render()
    assert 'date="' in output


def test_non_moment_entity_renders_type_tag():
    entity = _entity("a decision", type=EntityType.decision)
    r = Renderer()
    _render_entity(entity, r)
    output = r.render()
    assert "<decision" in output
    assert "a decision" in output
    assert "</decision>" in output


def test_pinned_entity_renders_important_tag():
    entity = _entity("some preference", type=EntityType.preference)
    entity = entity.model_copy(update={"pinned": True})
    r = Renderer()
    _render_entity(entity, r)
    output = r.render()
    assert "<important-preference" in output
    assert "</important-preference>" in output


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
    now = LocalDatetime(datetime.now().astimezone())
    assert _date_group_key(now, now) == "Today"


def test_date_group_key_yesterday():
    now = LocalDatetime(datetime.now().astimezone())
    yesterday = LocalDatetime(now - timedelta(days=1))
    result = _date_group_key(yesterday, now)
    assert result.startswith("Yesterday")


def test_date_group_key_older():
    now = LocalDatetime(datetime.now().astimezone())
    older = LocalDatetime(now - timedelta(days=5))
    result = _date_group_key(older, now)
    # Should be a full date string, not Today/Yesterday
    assert result not in ("Today",) and not result.startswith("Yesterday")


# ---------------------------------------------------------------------------
# _session_time
# ---------------------------------------------------------------------------


def test_session_time_just_now():
    now = LocalDatetime(datetime.now().astimezone())
    result = _session_time(UTCDatetime(now - timedelta(seconds=10)), now)
    assert "just now" in result


def test_session_time_minutes_ago():
    now = LocalDatetime(datetime.now().astimezone())
    result = _session_time(UTCDatetime(now - timedelta(minutes=30)), now)
    assert "minutes ago" in result


def test_session_time_hours_ago():
    now = LocalDatetime(datetime.now().astimezone())
    result = _session_time(UTCDatetime(now - timedelta(hours=3)), now)
    assert "hours ago" in result


def test_session_time_yesterday_returns_time_only():
    now = LocalDatetime(datetime.now().astimezone())
    yesterday = UTCDatetime(now - timedelta(days=1))
    result = _session_time(yesterday, now)
    # Should not include "ago" — just a time string
    assert "ago" not in result


def test_session_time_one_minute_ago():
    now = LocalDatetime(datetime.now().astimezone())
    result = _session_time(UTCDatetime(now - timedelta(seconds=65)), now)
    assert "1 minute ago" in result


# ---------------------------------------------------------------------------
# _render_all_time_story
# ---------------------------------------------------------------------------


def _story(title: str = "Our Story", content: str = "Chapter 1") -> Story:
    from charlieverse.memory.stories import StoryId, StoryTier

    now = datetime.now(UTC)
    return Story.model_construct(
        id=StoryId(),
        title=title,
        summary=None,
        content=content,
        tier=StoryTier.all_time,
        period_start=None,
        period_end=None,
        workspace=None,
        session_id=None,
        tags=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _render_story(story) -> str:
    """Render a story the same way _render_context does: via Renderer.append."""
    r = Renderer()
    r.append(story.content, "our_story_so_far")
    return r.render()


def test_render_all_time_story_contains_content_only():
    """Title is no longer rendered inside the tag — only content."""
    story = _story(title="The Long Arc", content="A long journey")
    output = _render_story(story)
    assert "A long journey" in output
    assert "The Long Arc" not in output


def test_render_all_time_story_contains_content():
    story = _story(content="A long journey together")
    output = _render_story(story)
    assert "A long journey together" in output


def test_render_all_time_story_wrapped_in_tag():
    story = _story()
    output = _render_story(story)
    assert "<our_story_so_far>" in output
    assert "</our_story_so_far>" in output


# ---------------------------------------------------------------------------
# _parse_period_date
# ---------------------------------------------------------------------------


def test_parse_period_date_iso_string():
    result = _parse_period_date("2026-03-01T00:00:00+00:00")
    assert result is not None
    assert result.year == 2026
    assert result.month == 3


def test_parse_period_date_naive_gets_utc():
    result = _parse_period_date("2026-01-15T10:30:00")
    assert result is not None
    assert result.tzinfo is not None


def test_parse_period_date_none_returns_none():
    assert _parse_period_date(None) is None


def test_parse_period_date_empty_string_returns_none():
    assert _parse_period_date("") is None


def test_parse_period_date_invalid_returns_none():
    assert _parse_period_date("not-a-date") is None


# ---------------------------------------------------------------------------
# _render_tricks
# ---------------------------------------------------------------------------


def test_render_tricks_returns_empty_when_no_tricks():
    with patch("charlieverse.helpers.skills._discover_skills", return_value=[]):
        result = _render_tricks(workspace=None)
    assert result == ""


def test_render_tricks_returns_empty_on_exception():
    with patch("charlieverse.helpers.skills._discover_skills", side_effect=Exception("boom")):
        result = _render_tricks(workspace=None)
    assert result == ""


def test_render_tricks_formats_tricks_with_description(tmp_path):
    skill_path = str(tmp_path / "my-trick" / "SKILL.md")
    tricks = [{"name": "my-trick", "description": "does cool things", "path": skill_path}]
    with patch("charlieverse.helpers.skills._discover_skills", return_value=tricks):
        result = _render_tricks(workspace=None)
    assert "<tricks>" in result
    assert "my-trick" in result
    assert "does cool things" in result


def test_render_tricks_formats_tricks_without_description(tmp_path):
    skill_path = str(tmp_path / "bare-trick" / "SKILL.md")
    tricks = [{"name": "bare-trick", "description": "", "path": skill_path}]
    with patch("charlieverse.helpers.skills._discover_skills", return_value=tricks):
        result = _render_tricks(workspace=None)
    assert "bare-trick" in result


# ---------------------------------------------------------------------------
# render() — pinned entities, moments, knowledge, session entities, related
# ---------------------------------------------------------------------------


def _knowledge(topic: str = "Python", content: str = "Use type hints.") -> Knowledge:
    from charlieverse.memory.knowledge import KnowledgeId
    from charlieverse.memory.sessions import SessionId

    now = datetime.now(UTC)
    return Knowledge.model_construct(
        id=KnowledgeId(),
        topic=topic,
        content=content,
        tags=None,
        pinned=False,
        created_session_id=SessionId(),
        updated_session_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def test_render_includes_pinned_entities():
    pinned = _entity("pinned fact", type=EntityType.decision)
    pinned = pinned.model_copy(update={"pinned": True})
    bundle = _bundle(pinned_entities=[pinned])
    output = render(bundle)
    assert "<important-decision" in output
    assert "pinned fact" in output


def test_render_includes_moments():
    moment = _entity("felt connected", type=EntityType.moment)
    bundle = _bundle(moments=[moment])
    output = render(bundle)
    assert "<important-moment" in output
    assert "felt connected" in output


def test_render_includes_pinned_knowledge():
    knowledge = _knowledge(topic="Architecture", content="Use clean layering.")
    bundle = _bundle(pinned_knowledge=[knowledge])
    output = render(bundle)
    assert "<knowledge>" in output
    assert "Architecture" in output
    assert "Use clean layering." in output


def test_render_includes_session_entities():
    entity = _entity("recent decision", type=EntityType.decision)
    bundle = _bundle(session_entities=[entity])
    output = render(bundle)
    assert "<related_memories>" in output
    assert "recent decision" in output


def test_render_includes_related_entities():
    entity = _entity("related memory", type=EntityType.solution)
    bundle = _bundle(related_entities=[entity])
    output = render(bundle)
    assert "<related_memories>" in output
    assert "related memory" in output


def test_render_includes_all_time_story():
    story = _story(title="All Time Story", content="Our shared history.")
    bundle = _bundle(all_time_story=story)
    output = render(bundle)
    assert "<our_story_so_far>" in output
    assert "Our shared history." in output


# ---------------------------------------------------------------------------
# _render_first_run (is_first_run path)
# ---------------------------------------------------------------------------


def test_render_first_run_contains_session_id():
    """An empty bundle triggers the first-run path."""
    session = _session()
    bundle = ContextBundle(session=session)
    assert bundle.is_first_run
    output = render(bundle)
    assert "<session_id>" in output


def test_render_first_run_contains_birthday_tag():
    session = _session()
    bundle = ContextBundle(session=session)
    output = render(bundle)
    assert "<its_your_birthday>" in output


def test_render_first_run_session_id_value_present():
    session = _session()
    bundle = ContextBundle(session=session)
    output = render(bundle)
    assert session.id in output


# ---------------------------------------------------------------------------
# ContextBundle.is_first_run and seen_ids
# ---------------------------------------------------------------------------


def test_is_first_run_true_when_empty():
    bundle = ContextBundle(session=_session())
    assert bundle.is_first_run is True


def test_is_first_run_false_with_moments():
    bundle = ContextBundle(session=_session(), moments=[_entity()])
    assert bundle.is_first_run is False


def test_is_first_run_false_with_recent_sessions():
    bundle = ContextBundle(session=_session(), recent_sessions=[_session()])
    assert bundle.is_first_run is False


def test_is_first_run_false_with_all_time_story():
    bundle = ContextBundle(session=_session(), all_time_story=_story())
    assert bundle.is_first_run is False


def test_seen_ids_includes_all_entity_groups():
    moment = _entity("moment", type=EntityType.moment)
    pinned = _entity("pinned", type=EntityType.decision)
    session_entity = _entity("session", type=EntityType.solution)
    related = _entity("related", type=EntityType.preference)
    bundle = ContextBundle(
        session=_session(),
        moments=[moment],
        pinned_entities=[pinned],
        session_entities=[session_entity],
        related_entities=[related],
    )
    ids = bundle.seen_ids
    assert moment.id in ids
    assert pinned.id in ids
    assert session_entity.id in ids
    assert related.id in ids


def test_seen_ids_includes_knowledge():
    knowledge = _knowledge()
    bundle = ContextBundle(
        session=_session(),
        moments=[_entity()],
        pinned_knowledge=[knowledge],
    )
    assert knowledge.id in bundle.seen_ids


def test_seen_ids_includes_all_time_story():
    story = _story()
    bundle = ContextBundle(
        session=_session(),
        moments=[_entity()],
        all_time_story=story,
    )
    assert story.id in bundle.seen_ids


# ---------------------------------------------------------------------------
# workspace_directory tag
# ---------------------------------------------------------------------------


def test_render_does_not_include_workspace_directory_tag():
    bundle = _bundle(workspace="/projects/myapp")
    output = render(bundle)
    assert "<workspace_directory>" not in output


def test_render_workspace_none_does_not_crash():
    bundle = _bundle(workspace=None)
    output = render(bundle)
    assert "<session_id>" in output


# ---------------------------------------------------------------------------
# recent_messages rendering
# ---------------------------------------------------------------------------


def _context_message(role: str = "user", content: str = "hello", offset_seconds: int = 60) -> Message:
    return Message.model_construct(
        id=MessageId(),
        session_id=SessionId(),
        role=MessageRole(role),
        content=content,
        created_at=datetime.now(UTC) - timedelta(seconds=offset_seconds),
    )


def test_render_recent_messages_includes_tags():
    msgs = [
        _context_message("user", "what are we working on?", 120),
        _context_message("assistant", "we are building features", 60),
    ]
    output = _render_recent_messages(msgs)
    assert "<recent_messages>" in output
    assert "</recent_messages>" in output


def test_render_recent_messages_shows_user_content():
    msgs = [_context_message("user", "tell me about the changes", 60)]
    output = _render_recent_messages(msgs)
    assert "tell me about the changes" in output


def test_render_recent_messages_shows_assistant_content():
    msgs = [_context_message("assistant", "here is what i found", 60)]
    output = _render_recent_messages(msgs)
    assert "here is what i found" in output


def test_render_recent_messages_truncates_long_content():
    long_content = "x" * 600
    msgs = [_context_message("assistant", long_content, 60)]
    output = _render_recent_messages(msgs)
    # Truncated at 200 chars + "…"
    assert "x" * 200 + "…" in output


def test_render_recent_messages_does_not_appear_when_empty():
    bundle = _bundle(recent_messages=[])
    output = render(bundle)
    assert "<recent_messages>" not in output


def test_render_recent_messages_user_labeled_as_me():
    msgs = [_context_message("user", "context message", 60)]
    output = _render_recent_messages(msgs)
    assert "<me " in output
