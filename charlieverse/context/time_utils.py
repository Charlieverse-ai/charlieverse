"""Shared time formatting utilities for the context system."""

from __future__ import annotations

from datetime import UTC, datetime


def _normalize_tz(dt: datetime) -> datetime:
    """Normalize to UTC-aware for safe arithmetic between naive and aware datetimes.

    Naive datetimes are assumed to be local time and get localized first.
    Aware datetimes get converted to UTC.
    """
    if dt.tzinfo is None:
        # Naive — assume local time, make aware, then convert to UTC
        return dt.astimezone(UTC)
    return dt.astimezone(UTC)


def format_datetime(dt: datetime) -> str:
    """Format a datetime for display in reminders/context."""

    import locale
    import time

    try:
        locale.setlocale(locale.LC_TIME, "")
    except locale.Error:
        return dt.strftime("%B %d, %Y %I:%M %p")

    if time.strftime("%p"):
        return dt.strftime("%B %d, %Y %I:%M %p")

    return dt.strftime("%B %d, %Y %H:%M")


def format_time(dt: datetime) -> str:
    """Format a datetime for display in reminders/context."""

    import locale
    import time

    try:
        locale.setlocale(locale.LC_TIME, "")
    except locale.Error:
        return dt.strftime("%I:%M %p")

    if time.strftime("%p"):
        return dt.strftime("%I:%M %p")

    return dt.strftime("%Y %H:%M")


def relative_time(start: datetime, now: datetime) -> str:
    """Format the delta between two datetimes as a human-readable duration.

    e.g. "just now", "12 minutes", "2 hours, 35 minutes"
    """
    delta = _normalize_tz(now) - _normalize_tz(start)
    total_seconds = int(delta.total_seconds())

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


def relative_date(date: datetime) -> str:
    """Format a datetime as a relative 'ago' string for activation context.

    e.g. "just now", "5 minutes ago", "2.5 hours ago", "3 days ago"
    Falls back to full date format for dates older than a week.
    """
    now = datetime.now(UTC)
    diff = now - _normalize_tz(date)
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
            return f"{int(days)} days ago ({full_date})"
        elif days < 30:
            weeks = days / 7
            return f"2 weeks ago ({full_date})" if weeks < 3 else f"{round(weeks, 1)} weeks ago ({full_date})"
        elif days < 60:
            return f"1 month ago ({full_date})"
        elif days < 365:
            months = days / 30.44
            return f"{round(months, 1)} months ago ({full_date})"
        elif days < 730:
            return f"1 year ago ({full_date})"
        else:
            years = days / 365.25
            return f"{round(years, 1)} years ago ({full_date})"
