from datetime import UTC, datetime
from typing import NewType

UTCDatetime = NewType("UTCDatetime", datetime)


def utc_now() -> UTCDatetime:
    return UTCDatetime(datetime.now(UTC))


def from_iso_or_none(format: str | None) -> UTCDatetime | None:
    if not format:
        return None

    return from_iso(format)


def from_iso(format: str) -> UTCDatetime:
    dt = datetime.fromisoformat(format)

    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC)

    if dt.tzinfo is not UTC:
        dt: datetime = dt.astimezone(UTC)

    return UTCDatetime(dt)
