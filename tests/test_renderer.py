"""Tests for the activation context renderer (charlieverse/context/renderer.py).

The renderer exposes a single public class: ActivationContextRenderer. These
tests exercise the rendered XML output for the structural invariants each
section promises.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from charlieverse.context.builder import ContextBundle
from charlieverse.context.renderer import ActivationContextRenderer
from charlieverse.memory.entities import Entity, EntityId, EntityType
from charlieverse.memory.knowledge import Knowledge, KnowledgeId
from charlieverse.memory.messages import Message, MessageId, MessageRole
from charlieverse.memory.sessions import Session, SessionId
from charlieverse.memory.stories import Story, StoryId, StoryTier
from charlieverse.types.dates import UTCDatetime
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString, WorkspaceFilePath

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(
    what_happened: str = "worked on things",
    for_next_session: str = "continue fixing bugs",
    workspace: str = "/workspace/path",
    updated_at: datetime | None = None,
) -> Session:
    now = UTCDatetime(updated_at or datetime.now(UTC))
    return Session.model_construct(
        id=SessionId(),
        what_happened=NonEmptyString(what_happened),
        for_next_session=NonEmptyString(for_next_session),
        workspace=WorkspaceFilePath(workspace),
        tags=TagList([NonEmptyString("tag")]),
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _entity(
    content: str = "test content",
    type: EntityType = EntityType.decision,
    updated_at: datetime | None = None,
) -> Entity:
    now = UTCDatetime(updated_at or datetime.now(UTC))
    return Entity.model_construct(
        id=EntityId(),
        type=type,
        content=NonEmptyString(content),
        tags=None,
        pinned=False,
        created_session_id=SessionId(),
        updated_session_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _knowledge(topic: str = "Python", content: str = "Use type hints.") -> Knowledge:
    now = UTCDatetime(datetime.now(UTC))
    return Knowledge.model_construct(
        id=KnowledgeId(),
        topic=NonEmptyString(topic),
        content=NonEmptyString(content),
        tags=None,
        pinned=False,
        created_session_id=SessionId(),
        updated_session_id=None,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _story(title: str = "Our Story", content: str = "Chapter 1") -> Story:
    now = UTCDatetime(datetime.now(UTC))
    return Story.model_construct(
        id=StoryId(),
        title=NonEmptyString(title),
        summary=None,
        content=NonEmptyString(content),
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


def _message(role: str = "user", content: str = "hello", offset_seconds: int = 60) -> Message:
    return Message.model_construct(
        id=MessageId(),
        session_id=SessionId(),
        role=MessageRole(role),
        content=NonEmptyString(content),
        created_at=UTCDatetime(datetime.now(UTC) - timedelta(seconds=offset_seconds)),
    )


def _bundle(**kwargs) -> ContextBundle:
    """Build a non-first-run ContextBundle with a session_id and at least one moment."""
    session_id = kwargs.pop("current_session_id", SessionId())
    moments = kwargs.pop("moments", [_entity("personality moment", type=EntityType.moment)])
    return ContextBundle(current_session_id=session_id, moments=moments, **kwargs)


def _render(bundle: ContextBundle) -> str:
    return ActivationContextRenderer(bundle).render()


# ---------------------------------------------------------------------------
# Session tag structure
# ---------------------------------------------------------------------------


def test_most_recent_session_has_most_recent_attr():
    now = datetime.now(UTC)
    recent = _session("most recent work", updated_at=now - timedelta(minutes=5))
    older = _session("older work", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[recent, older])
    output = _render(bundle)
    assert 'most_recent="true"' in output
    assert "<session " in output
    assert "</session>" in output


def test_only_first_session_gets_most_recent_attr():
    now = datetime.now(UTC)
    s1 = _session("first", updated_at=now - timedelta(minutes=5))
    s2 = _session("second", updated_at=now - timedelta(hours=1))
    s3 = _session("third", updated_at=now - timedelta(hours=2))
    bundle = _bundle(recent_sessions=[s1, s2, s3])
    output = _render(bundle)
    assert output.count('most_recent="true"') == 1
    assert output.count("<session ") == 3


def test_no_our_timeline_wrapper():
    now = datetime.now(UTC)
    recent = _session("some work", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = _render(bundle)
    assert "<our_timeline>" not in output
    assert "</our_timeline>" not in output


def test_single_session_uses_session_tag():
    now = datetime.now(UTC)
    only = _session("only session", updated_at=now - timedelta(minutes=10))
    bundle = _bundle(recent_sessions=[only])
    output = _render(bundle)
    assert "<session " in output
    assert 'most_recent="true"' in output


def test_sessions_wrapped_in_sessions_tag():
    now = datetime.now(UTC)
    recent = _session("recent", updated_at=now - timedelta(minutes=5))
    bundle = _bundle(recent_sessions=[recent])
    output = _render(bundle)
    assert "<sessions>" in output
    assert "</sessions>" in output


# ---------------------------------------------------------------------------
# Temporal weighting note
# ---------------------------------------------------------------------------


def test_time_weighting_note_present():
    bundle = _bundle()
    output = _render(bundle)
    assert "Weight information according to relative time" in output


# ---------------------------------------------------------------------------
# very-important tag (was <important>)
# ---------------------------------------------------------------------------


def test_very_important_tag_used_not_important():
    bundle = _bundle()
    output = _render(bundle)
    assert "<very-important>" in output


# ---------------------------------------------------------------------------
# render() — pinned entities, moments, knowledge, session entities, related
# ---------------------------------------------------------------------------


def test_render_includes_pinned_entities():
    pinned = _entity("pinned fact", type=EntityType.decision)
    pinned = pinned.model_copy(update={"pinned": True})
    bundle = _bundle(pinned_entities=[pinned])
    output = _render(bundle)
    assert "pinned fact" in output


def test_render_includes_moments():
    moment = _entity("felt connected", type=EntityType.moment)
    bundle = _bundle(moments=[moment])
    output = _render(bundle)
    assert "felt connected" in output


def test_render_includes_pinned_knowledge():
    knowledge = _knowledge(topic="Architecture", content="Use clean layering.")
    bundle = _bundle(pinned_knowledge=[knowledge])
    output = _render(bundle)
    assert "<knowledge>" in output
    assert "Architecture" in output
    assert "Use clean layering." in output


def test_render_includes_session_entities():
    entity = _entity("recent decision", type=EntityType.decision)
    bundle = _bundle(session_entities=[entity])
    output = _render(bundle)
    assert "<related_memories>" in output
    assert "recent decision" in output


def test_render_includes_related_entities():
    entity = _entity("related memory", type=EntityType.solution)
    bundle = _bundle(related_entities=[entity])
    output = _render(bundle)
    assert "<related_memories>" in output
    assert "related memory" in output


# ---------------------------------------------------------------------------
# First run path
# ---------------------------------------------------------------------------


def test_render_first_run_contains_session_id():
    """An empty bundle triggers the first-run path."""
    bundle = ContextBundle(current_session_id=SessionId())
    assert bundle.is_first_run
    output = _render(bundle)
    assert "<session_id>" in output


def test_render_first_run_contains_birthday_tag():
    bundle = ContextBundle(current_session_id=SessionId())
    output = _render(bundle)
    assert "<its_your_birthday>" in output


def test_render_first_run_session_id_value_present():
    session_id = SessionId()
    bundle = ContextBundle(current_session_id=session_id)
    output = _render(bundle)
    assert session_id in output


# ---------------------------------------------------------------------------
# ContextBundle.is_first_run and seen_ids
# ---------------------------------------------------------------------------


def test_is_first_run_true_when_empty():
    bundle = ContextBundle(current_session_id=SessionId())
    assert bundle.is_first_run is True


def test_is_first_run_false_with_moments():
    bundle = ContextBundle(current_session_id=SessionId(), moments=[_entity()])
    assert bundle.is_first_run is False


def test_is_first_run_false_with_recent_sessions():
    bundle = ContextBundle(current_session_id=SessionId(), recent_sessions=[_session()])
    assert bundle.is_first_run is False


def test_seen_ids_includes_all_entity_groups():
    moment = _entity("moment", type=EntityType.moment)
    pinned = _entity("pinned", type=EntityType.decision)
    session_entity = _entity("session", type=EntityType.solution)
    related = _entity("related", type=EntityType.preference)
    bundle = ContextBundle(
        current_session_id=SessionId(),
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


def test_seen_ids_excludes_knowledge():
    """seen_ids only covers entity groups — knowledge is not part of the dedup set."""
    knowledge = _knowledge()
    bundle = ContextBundle(
        current_session_id=SessionId(),
        moments=[_entity()],
        pinned_knowledge=[knowledge],
    )
    assert knowledge.id not in bundle.seen_ids


# ---------------------------------------------------------------------------
# workspace_directory tag — removed from renderer output
# ---------------------------------------------------------------------------


def test_render_does_not_include_workspace_directory_tag():
    bundle = _bundle(workspace=WorkspaceFilePath("/projects/myapp"))
    output = _render(bundle)
    assert "<workspace_directory>" not in output


def test_render_workspace_none_does_not_crash():
    bundle = _bundle(workspace=None)
    output = _render(bundle)
    assert "<session_id>" in output


# ---------------------------------------------------------------------------
# recent_messages rendering
# ---------------------------------------------------------------------------


def test_render_recent_messages_wrapped_in_tag():
    msgs = [
        _message("user", "what are we working on?", 120),
        _message("assistant", "we are building features", 60),
    ]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert "<recent_messages>" in output
    assert "</recent_messages>" in output


def test_render_recent_messages_shows_user_content():
    msgs = [_message("user", "tell me about the changes", 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert "tell me about the changes" in output


def test_render_recent_messages_shows_assistant_content():
    msgs = [_message("assistant", "here is what i found", 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert "here is what i found" in output


def test_render_recent_messages_does_not_appear_when_empty():
    bundle = _bundle(recent_messages=[])
    output = _render(bundle)
    assert "<recent_messages>" not in output


def test_render_recent_messages_user_labeled_as_me():
    msgs = [_message("user", "context message", 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert "<me " in output


# ---------------------------------------------------------------------------
# Message truncation at 300 characters
# ---------------------------------------------------------------------------


def test_render_recent_messages_long_message_truncated():
    long_content = "x" * 400
    msgs = [_message("user", long_content, 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    # The raw 400-char content should not appear verbatim
    assert long_content not in output
    # The truncation marker should be present
    assert "…" in output


def test_render_recent_messages_short_message_not_truncated():
    short_content = "short message under limit"
    msgs = [_message("user", short_content, 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert short_content in output
    assert "…" not in output


def test_render_recent_messages_exact_limit_not_truncated():
    content = "a" * 300
    msgs = [_message("user", content, 60)]
    bundle = _bundle(recent_messages=msgs)
    output = _render(bundle)
    assert content in output
    assert "…" not in output


# ---------------------------------------------------------------------------
# Pinned entities — <pinned> wrapper and pinned-{type} tag names
# ---------------------------------------------------------------------------


def test_render_pinned_entities_wrapped_in_pinned_tag():
    pinned = _entity("pinned decision", type=EntityType.decision)
    pinned = pinned.model_copy(update={"pinned": True})
    bundle = _bundle(pinned_entities=[pinned])
    output = _render(bundle)
    assert "<pinned>" in output
    assert "</pinned>" in output


def test_render_pinned_entity_uses_pinned_type_tag():
    pinned = _entity("pinned fact", type=EntityType.decision)
    pinned = pinned.model_copy(update={"pinned": True})
    bundle = _bundle(pinned_entities=[pinned])
    output = _render(bundle)
    assert "<pinned-decision " in output


def test_render_pinned_tag_emitted_even_with_no_pinned_entities():
    """_render_pinned_memories always emits <pinned> wrapper regardless of content."""
    bundle = _bundle(pinned_entities=[])
    output = _render(bundle)
    assert "<pinned>" in output
    assert "</pinned>" in output


def test_render_entity_includes_id_attribute():
    entity = _entity("something memorable", type=EntityType.preference)
    bundle = _bundle(related_entities=[entity])
    output = _render(bundle)
    assert f'id="{entity.id}"' in output


def test_render_non_pinned_entity_uses_plain_type_tag():
    entity = _entity("regular decision", type=EntityType.decision)
    bundle = _bundle(related_entities=[entity])
    output = _render(bundle)
    assert "<decision " in output
    assert "<pinned-decision" not in output


def test_render_moment_entity_uses_pinned_moment_tag():
    """Moments are treated as important even when not pinned, so they get pinned-moment tag."""
    moment = _entity("a moment", type=EntityType.moment)
    bundle = _bundle(moments=[moment], related_entities=[moment])
    output = _render(bundle)
    assert "<pinned-moment " in output
