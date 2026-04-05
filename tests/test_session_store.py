"""CRUD tests for SessionStore."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from charlieverse.db import SessionStore
from charlieverse.db.stores.session_store import _is_noise
from charlieverse.models.session import NewSession, Session, SessionContent, UpdateSession, session_id

# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_returns_session_id(session_store: SessionStore):
    id = session_id()
    s = await session_store.create(NewSession(id=id, workspace="/workspace"))
    assert s == id


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


async def test_get_nonexistent_returns_none(session_store: SessionStore):
    result = await session_store.get(session_id())
    assert result is None


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_changes_content(session_store: SessionStore):
    id = session_id()
    await session_store.create(NewSession(id=id, workspace="/workspace"))

    updated = await session_store.update(UpdateSession(id=id, workspace="/workspace", content=SessionContent(what_happened="what", for_next_session="next")))

    assert updated.what_happened == "what"


async def test_update_changes_tags(session_store: SessionStore):
    s = await session_store.create(_session(tags=["old"]))
    s.tags = ["new", "tags"]
    await session_store.update(s)
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.tags == ["new", "tags"]


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def test_upsert_creates_new(session_store: SessionStore):
    s = _session()
    result = await session_store.upsert(s)
    fetched = await session_store.get(result.id)
    assert fetched is not None


async def test_upsert_updates_existing(session_store: SessionStore):
    s = await session_store.create(_session(what_happened="v1"))
    s.what_happened = "v2"
    await session_store.upsert(s)
    fetched = await session_store.get(s.id)
    assert fetched is not None
    assert fetched.what_happened == "v2"


# ---------------------------------------------------------------------------
# Recent
# ---------------------------------------------------------------------------


async def test_recent_returns_sessions_with_content(session_store: SessionStore):
    await session_store.create(_session())
    await session_store.create(_session())
    results = await session_store.recent(limit=10)
    assert len(results) >= 2


async def test_recent_excludes_empty_sessions(session_store: SessionStore):
    # Session with no what_happened should be excluded
    await session_store.create(Session())
    await session_store.create(_session())
    results = await session_store.recent(limit=10)
    assert all(s.what_happened is not None for s in results)


async def test_recent_returns_all_workspaces(session_store: SessionStore):
    """Workspace is metadata, not a filter — all sessions returned regardless."""
    await session_store.create(_session(workspace="/project/a"))
    await session_store.create(_session(workspace="/project/b"))
    results = await session_store.recent(limit=10, workspace="/project/a")
    workspaces = {s.workspace for s in results}
    assert "/project/a" in workspaces
    assert "/project/b" in workspaces


# ---------------------------------------------------------------------------
# Recent within range
# ---------------------------------------------------------------------------


async def test_recent_within_range_returns_matching(session_store: SessionStore):
    await session_store.create(_session())
    # Use a wide range that covers today
    results = await session_store.recent_within_range("2020-01-01", "2030-12-31")
    assert len(results) >= 1


async def test_recent_within_range_excludes_outside(session_store: SessionStore):
    await session_store.create(_session())
    # Range in the far past — should find nothing
    results = await session_store.recent_within_range("2000-01-01", "2000-12-31")
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Soft delete
# ---------------------------------------------------------------------------


async def test_soft_delete_hides_session(session_store: SessionStore):
    s = await session_store.create(_session())
    await session_store.delete(s.id)
    result = await session_store.get(s.id)
    assert result is None


async def test_soft_deleted_excluded_from_recent(session_store: SessionStore):
    s = await session_store.create(_session())
    count_before = len(await session_store.recent(limit=100))
    await session_store.delete(s.id)
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


async def test_recent_messages_returns_empty_when_no_messages(session_store: SessionStore):
    result = await session_store.recent_messages(turns=3)
    assert result == []


async def test_recent_messages_returns_chronological_order(db, session_store: SessionStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "first message", base - timedelta(minutes=5))
    await _insert_message(db, "assistant", "first reply", base - timedelta(minutes=4))
    await _insert_message(db, "user", "second message", base - timedelta(minutes=3))
    await _insert_message(db, "assistant", "second reply", base - timedelta(minutes=2))

    result = await session_store.recent_messages(turns=2)
    assert len(result) >= 2
    # Chronological order: older messages first
    for i in range(len(result) - 1):
        assert result[i].created_at <= result[i + 1].created_at


async def test_recent_messages_filters_noise(db, session_store: SessionStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "real question", base - timedelta(minutes=10))
    await _insert_message(db, "assistant", "real answer", base - timedelta(minutes=9))
    await _insert_message(db, "user", "/session-save", base - timedelta(minutes=8))
    await _insert_message(db, "assistant", "context saved", base - timedelta(minutes=7))

    result = await session_store.recent_messages(turns=5)
    contents = [m.content for m in result]
    assert "/session-save" not in contents


async def test_recent_messages_filters_system_reminder(db, session_store: SessionStore):
    base = datetime.now(UTC)
    await _insert_message(db, "user", "normal question", base - timedelta(minutes=5))
    await _insert_message(db, "user", "<system-reminder>injected</system-reminder>", base - timedelta(minutes=4))
    await _insert_message(db, "assistant", "ok", base - timedelta(minutes=3))

    result = await session_store.recent_messages(turns=3)
    contents = [m.content for m in result]
    assert not any("<system-reminder>" in c for c in contents)


async def test_recent_messages_respects_turn_limit(db, session_store: SessionStore):
    base = datetime.now(UTC)
    # Insert 5 user+assistant turns
    for i in range(5):
        offset = timedelta(minutes=10 - i * 2)
        await _insert_message(db, "user", f"question {i}", base - offset)
        await _insert_message(db, "assistant", f"answer {i}", base - offset + timedelta(seconds=30))

    result = await session_store.recent_messages(turns=2)
    user_messages = [m for m in result if m.role == "user"]
    # Should have at most 2 user turns
    assert len(user_messages) <= 2


async def test_recent_messages_returns_context_message_objects(db, session_store: SessionStore):
    from charlieverse.models import ContextMessage

    base = datetime.now(UTC)
    await _insert_message(db, "user", "hello charlie", base - timedelta(minutes=2))
    await _insert_message(db, "assistant", "hello there!", base - timedelta(minutes=1))

    result = await session_store.recent_messages(turns=1)
    assert all(isinstance(m, ContextMessage) for m in result)
    assert all(m.role in ("user", "assistant") for m in result)
