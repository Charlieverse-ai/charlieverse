"""CRUD tests for SessionStore."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from charlieverse.memory.messages import Message
from charlieverse.memory.messages.store import MessageStore, _is_noise
from charlieverse.memory.sessions import DeleteSession, NewSession, SessionContent, SessionId, UpdateSession
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString, WorkspaceFilePath


def _tags(*values: str) -> TagList:
    return TagList([NonEmptyString(v) for v in values])


def _ws(path: str = "/workspace") -> WorkspaceFilePath:
    return WorkspaceFilePath(path)


_WHAT = "Refactored the entire memory pipeline and added new model validation rules"
_NEXT = "Continue fixing the remaining test failures and update the story store tests"


def _new_session(
    workspace: str = "/workspace",
    what_happened: str = _WHAT,
    for_next_session: str = _NEXT,
    tags: TagList | None = None,
) -> UpdateSession:
    """Build an UpdateSession with content (so it shows up in recent queries)."""
    return UpdateSession(
        id=SessionId(),
        workspace=_ws(workspace),
        content=SessionContent(
            what_happened=NonEmptyString(what_happened),
            for_next_session=NonEmptyString(for_next_session),
        ),
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_session_id(session_store: SessionStore):
    id = SessionId()
    s = await session_store.create(NewSession(id=id, workspace=_ws()))
    assert s == id


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(session_store: SessionStore):
    result = await session_store.get(SessionId())
    assert result is None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(session_store: SessionStore):
    id = SessionId()
    await session_store.create(NewSession(id=id, workspace=_ws()))
    updated = await session_store.update(
        UpdateSession(
            id=id,
            workspace=_ws(),
            content=SessionContent(
                what_happened=NonEmptyString(_WHAT),
                for_next_session=NonEmptyString(_NEXT),
            ),
        )
    )
    assert updated.what_happened == _WHAT


async def test_update_changes_tags(session_store: SessionStore):
    u = _new_session(tags=_tags("old"))
    await session_store.upsert(u)
    await session_store.update(UpdateSession(id=u.id, workspace=_ws(), tags=_tags("new", "tags")))
    fetched = await session_store.get(u.id)
    assert fetched is not None
    assert fetched.tags == ["new", "tags"]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def test_upsert_creates_new(session_store: SessionStore):
    u = _new_session()
    result = await session_store.upsert(u)
    fetched = await session_store.get(result.id)
    assert fetched is not None


async def test_upsert_updates_existing(session_store: SessionStore):
    u = _new_session()
    s = await session_store.upsert(u)
    new_what = "Updated the what happened field with enough characters to pass validation"
    await session_store.upsert(
        UpdateSession(
            id=s.id,
            workspace=_ws(),
            content=SessionContent(
                what_happened=NonEmptyString(new_what),
                for_next_session=NonEmptyString(_NEXT),
            ),
        )
    )
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.what_happened == new_what


# ---------------------------------------------------------------------------
# Recent
# ---------------------------------------------------------------------------


async def test_recent_returns_sessions_with_content(session_store: SessionStore):
    await session_store.upsert(_new_session())
    await session_store.upsert(_new_session())
    results = await session_store.recent(limit=10)
    assert len(results) >= 2


async def test_recent_excludes_empty_sessions(session_store: SessionStore):
    # Session with no what_happened should be excluded
    await session_store.create(NewSession(workspace=_ws()))
    await session_store.upsert(_new_session())
    results = await session_store.recent(limit=10)
    assert all(s.what_happened is not None for s in results)


async def test_recent_returns_all_workspaces(session_store: SessionStore):
    """Workspace is metadata, not a filter -- all sessions returned regardless."""
    await session_store.upsert(_new_session(workspace="/project/a"))
    await session_store.upsert(_new_session(workspace="/project/b"))
    results = await session_store.recent(limit=10, workspace=_ws("/project/a"))
    workspaces = {s.workspace for s in results}
    assert "/project/a" in workspaces
    assert "/project/b" in workspaces


# ---------------------------------------------------------------------------
# Recent within range
# ---------------------------------------------------------------------------


async def test_recent_within_range_returns_matching(session_store: SessionStore):
    await session_store.upsert(_new_session())
    results = await session_store.recent_within_range("2020-01-01", "2030-12-31")
    assert len(results) >= 1


async def test_recent_within_range_excludes_outside(session_store: SessionStore):
    await session_store.upsert(_new_session())
    results = await session_store.recent_within_range("2000-01-01", "2000-12-31")
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_session(session_store: SessionStore):
    u = _new_session()
    await session_store.upsert(u)
    await session_store.delete(DeleteSession(id=u.id))
    result = await session_store.get(u.id)
    assert result is None


async def test_soft_deleted_excluded_from_recent(session_store: SessionStore):
    u = _new_session()
    await session_store.upsert(u)
    count_before = len(await session_store.recent(limit=100))
    await session_store.delete(DeleteSession(id=u.id))
    count_after = len(await session_store.recent(limit=100))
    assert count_after == count_before - 1


# ---------------------------------------------------------------------------
# _is_noise helper
# ---------------------------------------------------------------------------


def test_is_noise_session_save_trick():
    assert _is_noise("/trick session-save") is True


def test_is_noise_session_save_slash():
    assert _is_noise("/session-save") is True


def test_is_noise_charlieverse_trick():
    assert _is_noise("/trick Charlieverse:session-save") is True


def test_is_noise_task_notification():
    assert _is_noise("<task-notification>some content</task-notification>") is True


def test_is_noise_system_reminder():
    assert _is_noise("<system-reminder>some system content</system-reminder>") is True


def test_is_noise_case_insensitive():
    assert _is_noise("/TRICK SESSION-SAVE") is True
    assert _is_noise("<TASK-NOTIFICATION>stuff</TASK-NOTIFICATION>") is True


def test_is_noise_normal_message():
    assert _is_noise("hey charlie, how are you?") is False


def test_is_noise_regular_assistant_reply():
    assert _is_noise("I found the bug in the session store.") is False


def test_is_noise_empty_string():
    assert _is_noise("") is False


def test_is_noise_strips_whitespace():
    assert _is_noise("  /session-save  ") is True


# ---------------------------------------------------------------------------
# recent_messages
# ---------------------------------------------------------------------------


async def _insert_message(db, role: str, content: str, created_at: datetime | None = None) -> None:
    """Helper to insert a raw message row."""
    if created_at is None:
        created_at = datetime.now(UTC)
    await db.execute(
        "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), str(uuid4()), role, content, created_at.isoformat()),
    )
    await db.commit()


async def test_recent_messages_returns_empty_when_no_messages(message_store: MessageStore):
    result = await message_store.recent_messages(turns=3)
    assert result == []


async def test_recent_messages_returns_reverse_chronological_order(db, message_store: MessageStore):
    """recent_messages returns the most recent turns first (DESC by created_at)."""
    base = datetime.now(UTC)
    await _insert_message(db, "user", "first message", base - timedelta(minutes=5))
    await _insert_message(db, "assistant", "first reply", base - timedelta(minutes=4))
    await _insert_message(db, "user", "second message", base - timedelta(minutes=3))
    await _insert_message(db, "assistant", "second reply", base - timedelta(minutes=2))

    result = await message_store.recent_messages(turns=2)
    assert len(result) >= 2
    for i in range(len(result) - 1):
        assert result[i].created_at >= result[i + 1].created_at


async def test_recent_messages_filters_noise(db, message_store: MessageStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "real question", base - timedelta(minutes=10))
    await _insert_message(db, "assistant", "real answer", base - timedelta(minutes=9))
    await _insert_message(db, "user", "/session-save", base - timedelta(minutes=8))
    await _insert_message(db, "assistant", "context saved", base - timedelta(minutes=7))

    result = await message_store.recent_messages(turns=5)
    contents = [m.content for m in result]
    assert "/session-save" not in contents


async def test_recent_messages_filters_system_reminder(db, message_store: MessageStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "normal question", base - timedelta(minutes=5))
    await _insert_message(db, "user", "<system-reminder>injected</system-reminder>", base - timedelta(minutes=4))
    await _insert_message(db, "assistant", "ok", base - timedelta(minutes=3))

    result = await message_store.recent_messages(turns=3)
    contents = [m.content for m in result]
    assert not any("<system-reminder>" in c for c in contents)


async def test_recent_messages_respects_turn_limit(db, message_store: MessageStore):
    base = datetime.now(UTC)
    for i in range(5):
        offset = timedelta(minutes=10 - i * 2)
        await _insert_message(db, "user", f"question {i}", base - offset)
        await _insert_message(db, "assistant", f"answer {i}", base - offset + timedelta(seconds=30))

    result = await message_store.recent_messages(turns=2)
    user_messages = [m for m in result if m.role == "user"]
    assert len(user_messages) <= 2


async def test_recent_messages_returns_message_objects(db, message_store: MessageStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "hello charlie", base - timedelta(minutes=2))
    await _insert_message(db, "assistant", "hello there!", base - timedelta(minutes=1))

    result = await message_store.recent_messages(turns=1)
    assert all(isinstance(m, Message) for m in result)
    # MessageRole normalizes "assistant" -> "charlie" via _missing_
    assert all(m.role in ("user", "charlie") for m in result)
