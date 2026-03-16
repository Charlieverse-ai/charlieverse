"""Shared time formatting utilities for the context system."""

from __future__ import annotations

from datetime import datetime, timezone


def _normalize_tz(dt: datetime) -> datetime:
    """Normalize to UTC-aware for safe arithmetic between naive and aware datetimes.

    Naive datetimes are assumed to be local time and get localized first.
    Aware datetimes get converted to UTC.
    """
    if dt.tzinfo is None:
        # Naive — assume local time, make aware, then convert to UTC
        return dt.astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def format_datetime(dt: datetime) -> str:
    """Format a datetime for display in reminders/context."""
    return dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")


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
    now = datetime.now(timezone.utc)
    diff = now - date.replace(tzinfo=timezone.utc)
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
        return "1 day ago"
    elif total_seconds < 604800:
        return f"{int(total_seconds / 86400)} days ago"
    else:
        return format_datetime(date)
