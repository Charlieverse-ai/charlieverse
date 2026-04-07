"""Tests for the FTS5 query sanitizer."""

from __future__ import annotations

import asyncio

import aiosqlite
import hypothesis.strategies as st
import pytest_asyncio
from hypothesis import given, settings

from charlieverse.db.fts import sanitize_fts_query

# ---------------------------------------------------------------------------
# Basic unit tests
# ---------------------------------------------------------------------------


def test_basic_sanitization_returns_non_empty_string():
    result = sanitize_fts_query("hello world")
    assert isinstance(result, str)
    assert result != ""


def test_periods_handled():
    # v1.6 bug: periods in version strings caused FTS5 syntax errors
    result = sanitize_fts_query("v1.6")
    assert isinstance(result, str)


def test_hyphens_handled():
    result = sanitize_fts_query("end-to-end")
    assert isinstance(result, str)


def test_stopword_only_input_returns_empty():
    # All tokens are stopwords — should return ""
    result = sanitize_fts_query("the and or")
    assert result == ""


def test_empty_string_returns_empty():
    result = sanitize_fts_query("")
    assert result == ""


def test_special_chars_stripped():
    result = sanitize_fts_query("foo\"bar'baz")
    assert result is not None
    assert '"foo"*' in result or '"bar"*' in result or '"baz"*' in result


def test_or_joined_multiple_tokens():
    result = sanitize_fts_query("pytest database")
    assert result is not None
    assert " OR " in result


def test_short_tokens_excluded():
    # Single-character tokens are excluded by design (len > 1 check)
    result = sanitize_fts_query("a b c")
    assert result == ""


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@given(st.text())
def test_sanitize_never_crashes(raw: str) -> None:
    """sanitize_fts_query must never raise for any input."""
    result = sanitize_fts_query(raw)
    assert isinstance(result, str)


@given(st.text(min_size=1))
@settings(max_examples=200)
def test_sanitized_query_never_errors_against_real_fts5(raw: str) -> None:
    """The sanitized query must never produce an sqlite3 OperationalError
    when executed against a real FTS5 table."""

    async def _run() -> None:
        async with aiosqlite.connect(":memory:") as db:
            await db.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
            await db.execute("INSERT INTO test_fts VALUES('hello world test')")
            await db.commit()
            sanitized = sanitize_fts_query(raw)
            if sanitized:
                # This is the critical assertion: the sanitized query must
                # execute without raising sqlite3.OperationalError
                await db.execute(
                    "SELECT * FROM test_fts WHERE test_fts MATCH ?",
                    (sanitized,),
                )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Integration fixture — run a sanitized query on a real FTS5 table via
# the async fixture plumbing (complements the Hypothesis test above)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fts_db():
    """Minimal FTS5 table fixture for integration-style tests."""
    db = await aiosqlite.connect(":memory:")
    await db.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
    await db.execute("INSERT INTO test_fts VALUES('hello world test')")
    await db.commit()
    yield db
    await db.close()


async def test_known_query_returns_rows(fts_db) -> None:
    """A well-formed query against our fixture data must return at least one row."""
    sanitized = sanitize_fts_query("hello")
    assert sanitized  # should not be empty for "hello"
    cursor = await fts_db.execute("SELECT * FROM test_fts WHERE test_fts MATCH ?", (sanitized,))
    rows = await cursor.fetchall()
    assert len(rows) > 0


async def test_version_string_does_not_error(fts_db) -> None:
    """Version strings like 'v1.6' were a historic crash source — verify clean."""
    sanitized = sanitize_fts_query("v1.6")
    if sanitized:
        # Should not raise
        await fts_db.execute("SELECT * FROM test_fts WHERE test_fts MATCH ?", (sanitized,))
