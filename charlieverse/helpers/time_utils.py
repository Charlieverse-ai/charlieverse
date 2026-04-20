"""Shared time formatting utilities for the context system.

All display functions accept UTCDatetime — they convert to local for
presentation internally. No module in the context system should handle
naive datetimes.
"""

from __future__ import annotations

from charlieverse.types.dates import LocalDatetime, UTCDatetime, to_local, utc_now
from charlieverse.types.time import Seconds


def format_datetime(dt: UTCDatetime) -> str:
    """Format a UTC instant for display in reminders/context."""

    import locale
    import time

    local = to_local(dt)
    try:
        locale.setlocale(locale.LC_TIME, "")
    except locale.Error:
        return local.strftime("%B %d, %Y %I:%M %p")

    if time.strftime("%p"):
        return local.strftime("%B %d, %Y %I:%M %p")

    return local.strftime("%B %d, %Y %H:%M")


def format_time(dt: UTCDatetime) -> str:
    """Format the time portion of a UTC instant for display."""

    import locale
    import time

    local = to_local(dt)
    try:
        locale.setlocale(locale.LC_TIME, "")
    except locale.Error:
        return local.strftime("%I:%M %p")

    if time.strftime("%p"):
        return local.strftime("%I:%M %p")

    return local.strftime("%Y %H:%M")


def format_local(dt: LocalDatetime, fmt: str) -> str:
    """Format an already-local datetime with the given strftime pattern."""
    return dt.strftime(fmt)


def relative_time(start: UTCDatetime, now: UTCDatetime | None = None) -> str:
    """Format the delta between two UTC instants as a human-readable duration.

    e.g. "just now", "12 minutes", "2 hours, 35 minutes"
    """
    if not now:
        now = utc_now()

    delta = now - start
    total_seconds = int(delta.total_seconds())

    return relative_time_seconds(total_seconds)


def relative_time_seconds(total_seconds: float | Seconds) -> str:
    """Format a duration in seconds as a human-readable fractional unit.

    e.g. "45 seconds", "1.5 minutes", "6.01 hours".
    Uses the largest unit where the value is >= 1 and renders it to at
    most two decimal places, stripping trailing zeros.
    """
    secs = float(total_seconds)

    if secs < 60:
        return _fmt_unit(secs, "second")

    minutes = secs / 60
    if minutes < 60:
        return _fmt_unit(minutes, "minute")

    hours = minutes / 60
    return _fmt_unit(hours, "hour")


def _fmt_unit(value: float, unit: str) -> str:
    """Format a float with at most 2 decimal places, stripping trailing
    zeros, and pluralize the unit based on the rounded value."""
    rounded = round(value, 2)
    # %g strips trailing zeros: 1.0 -> "1", 1.50 -> "1.5", 6.01 -> "6.01"
    display = f"{rounded:g}"
    suffix = "" if rounded == 1 else "s"
    return f"{display} {unit}{suffix}"


def relative_date(date: UTCDatetime, now: UTCDatetime | None = None) -> str:
    """Format a UTC instant as a relative 'ago' string for activation context.

    e.g. "just now", "5 minutes ago", "2.5 hours ago", "3 days ago"
    Falls back to full date format for dates older than a week.
    """
    if not now:
        now = utc_now()

    diff = now - date
    total_seconds = diff.total_seconds()

    if total_seconds < 0:
        return format_datetime(date)
    elif total_seconds <= 1:
        return "just now"
    elif total_seconds < 60:
        return f"{int(total_seconds)} seconds"
    elif total_seconds < 3600:
        mins = total_seconds / 60
        return "1 minute" if mins < 2 else f"{round(mins, 2)} minutes"
    elif total_seconds < 86400:
        hours = total_seconds / 3600
        return "1 hour" if hours < 2 else f"{round(hours, 2)} hours"
    elif total_seconds < 172800:
        return f"Yesterday at {format_time(date)}"
    else:
        days = total_seconds / 86400
        full_date = format_datetime(date)
        if days < 14:
            return f"{int(days)} days"
        elif days < 30:
            weeks = days / 7
            return "2 weeks" if weeks < 3 else f"{round(weeks, 1)} weeks"
        elif days < 60:
            return "1 month"
        elif days < 365:
            months = days / 30.44
            return f"{round(months, 1)} months"
        else:
            return f"{full_date}"
