"""Typed datetimes — UTC for storage and arithmetic, Local for display.

Rules of the road:
  - UTCDatetime is the canonical form. Anything that hits the DB, goes on the
    wire, or enters arithmetic is a UTCDatetime.
  - LocalDatetime is the display form. Only use it when rendering something
    a human will read.
  - Never construct a naive datetime. Never call `datetime.now()` without a tz.
    Use utc_now() or local_now() instead.
  - When parsing ISO strings, from_iso() always normalizes to UTC. If you need
    the parsed value in local time for display, call to_local() after.
"""

from datetime import UTC, date, datetime
from typing import NewType

UTCDatetime = NewType("UTCDatetime", datetime)
LocalDatetime = NewType("LocalDatetime", datetime)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def utc_now() -> UTCDatetime:
    """Current moment, always tz-aware UTC."""
    return UTCDatetime(datetime.now(UTC))


def local_now() -> LocalDatetime:
    """Current moment, always tz-aware in the system local timezone."""
    return LocalDatetime(datetime.now().astimezone())


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def from_iso(value: str) -> UTCDatetime:
    """Parse an ISO-8601 string and normalize to tz-aware UTC.

    Accepts naive strings (assumed UTC), local-aware strings, and UTC-aware
    strings. Always returns UTC.
    """
    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    elif dt.tzinfo is not UTC:
        dt = dt.astimezone(UTC)

    return UTCDatetime(dt)


def from_iso_or_none(value: str | None) -> UTCDatetime | None:
    """Parse an optional ISO-8601 string, returning None for empty input."""
    if not value:
        return None
    return from_iso(value)


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def to_local(value: UTCDatetime) -> LocalDatetime:
    """Convert a UTC instant to the system local timezone for display."""
    return LocalDatetime(value.astimezone())


def to_utc(value: LocalDatetime) -> UTCDatetime:
    """Convert a local instant back to UTC for storage or arithmetic."""
    return UTCDatetime(value.astimezone(UTC))


def at_utc_midnight(d: date | datetime) -> UTCDatetime:
    """Anchor a date (or the date portion of a datetime) at UTC midnight."""
    return UTCDatetime(datetime(d.year, d.month, d.day, tzinfo=UTC))
