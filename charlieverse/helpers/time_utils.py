"""Shared time formatting utilities for the context system.

All display functions accept UTCDatetime — they convert to local for
presentation internally. No module in the context system should handle
naive datetimes.
"""

from __future__ import annotations

from charlieverse.types.dates import LocalDatetime, UTCDatetime, to_local, utc_now


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


def relative_time_seconds(total_seconds: int) -> str:
    """Format the delta between two UTC instants as a human-readable duration.

    e.g. "just now", "12 minutes", "2 hours, 35 minutes"
    """
    if total_seconds < 60:
        return "just now"

    minutes = total_seconds // 60
    hours = minutes // 60

    if hours == 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    remaining_mins = minutes % 60
    if remaining_mins == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return f"{hours} hour{'s' if hours != 1 else ''}, {remaining_mins} minute{'s' if remaining_mins != 1 else ''}"


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
        return f"{int(total_seconds)} seconds ago"
    elif total_seconds < 3600:
        mins = total_seconds / 60
        return "1 minute ago" if mins < 2 else f"{round(mins, 2)} minutes ago"
    elif total_seconds < 86400:
        hours = total_seconds / 3600
        return "1 hour ago" if hours < 2 else f"{round(hours, 2)} hours ago"
    elif total_seconds < 172800:
        return f"Yesterday at {format_time(date)}"
    else:
        days = total_seconds / 86400
        full_date = format_datetime(date)
        if days < 14:
            return f"{int(days)} days ago"
        elif days < 30:
            weeks = days / 7
            return "2 weeks ago" if weeks < 3 else f"{round(weeks, 1)} weeks ago"
        elif days < 60:
            return "1 month ago"
        elif days < 365:
            months = days / 30.44
            return f"{round(months, 1)} months ago"
        else:
            return f"{full_date}"
