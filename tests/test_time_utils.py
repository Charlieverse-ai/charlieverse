"""Tests for charlieverse.context.time_utils — relative_date and format_datetime."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from charlieverse.helpers.time_utils import (
    format_datetime,
    format_time,
    relative_date,
    relative_time,
)
from charlieverse.types.dates import UTCDatetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> UTCDatetime:
    return UTCDatetime(datetime.now(UTC))


def _ago(seconds: float) -> UTCDatetime:
    return UTCDatetime(_now() - timedelta(seconds=seconds))


# ---------------------------------------------------------------------------
# format_datetime
# ---------------------------------------------------------------------------


def test_format_datetime_returns_string():
    dt = UTCDatetime(datetime(2026, 3, 22, 14, 30, tzinfo=UTC))
    result = format_datetime(dt)
    assert isinstance(result, str)
    assert "2026" in result
    assert "March" in result or "03" in result


# ---------------------------------------------------------------------------
# format_time
# ---------------------------------------------------------------------------


def test_format_time_returns_string():
    dt = UTCDatetime(datetime(2026, 3, 22, 14, 30, tzinfo=UTC))
    result = format_time(dt)
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_time_contains_digits():
    dt = UTCDatetime(datetime(2026, 3, 22, 9, 5, tzinfo=UTC))
    result = format_time(dt)
    # Should contain time digits
    assert any(c.isdigit() for c in result)


# ---------------------------------------------------------------------------
# relative_time
# ---------------------------------------------------------------------------


def test_relative_time_just_now():
    now = _now()
    # relative_time renders sub-minute spans as "N seconds" (relative_date is the
    # surface that returns "just now" for very-recent instants).
    assert relative_time(UTCDatetime(now - timedelta(seconds=30)), now) == "30 seconds"


def test_relative_time_minutes():
    now = _now()
    result = relative_time(UTCDatetime(now - timedelta(minutes=5)), now)
    assert "minute" in result
    assert "5" in result


def test_relative_time_one_minute():
    now = _now()
    result = relative_time(UTCDatetime(now - timedelta(seconds=61)), now)
    assert result == "1 minute"


def test_relative_time_hours():
    now = _now()
    result = relative_time(UTCDatetime(now - timedelta(hours=2)), now)
    assert "hour" in result
    assert "2" in result


def test_relative_time_one_hour():
    now = _now()
    result = relative_time(UTCDatetime(now - timedelta(hours=1)), now)
    assert result == "1 hour"


def test_relative_time_hours_and_minutes():
    now = _now()
    result = relative_time(UTCDatetime(now - timedelta(hours=2, minutes=30)), now)
    assert "hour" in result
    assert "minute" in result


# ---------------------------------------------------------------------------
# relative_date — sub-minute
# ---------------------------------------------------------------------------


def test_relative_date_just_now():
    assert relative_date(_ago(0.5)) == "just now"


def test_relative_date_seconds_ago():
    result = relative_date(_ago(30))
    assert result == "30 seconds"


# ---------------------------------------------------------------------------
# relative_date — minutes
# ---------------------------------------------------------------------------


def test_relative_date_one_minute_ago():
    result = relative_date(_ago(65))
    assert result == "1 minute"


def test_relative_date_minutes_ago():
    result = relative_date(_ago(300))  # 5 minutes
    assert "minute" in result


# ---------------------------------------------------------------------------
# relative_date — hours
# ---------------------------------------------------------------------------


def test_relative_date_one_hour_ago():
    result = relative_date(_ago(3700))
    assert result == "1 hour"


def test_relative_date_hours_ago():
    result = relative_date(_ago(7200))  # 2 hours
    assert "hour" in result


# ---------------------------------------------------------------------------
# relative_date — yesterday
# ---------------------------------------------------------------------------


def test_relative_date_yesterday():
    result = relative_date(_ago(86400 + 1))  # just over 1 day
    assert result.startswith("Yesterday")


# ---------------------------------------------------------------------------
# relative_date — days ago (2-14)
# ---------------------------------------------------------------------------


def test_relative_date_days_ago():
    result = relative_date(_ago(86400 * 5))  # 5 days
    assert result == "5 days"


def test_relative_date_13_days_ago():
    result = relative_date(_ago(86400 * 13))
    assert "days" in result


# ---------------------------------------------------------------------------
# relative_date — weeks (14-30 days)
# ---------------------------------------------------------------------------


def test_relative_date_2_weeks_ago():
    result = relative_date(_ago(86400 * 14))
    assert "2 weeks" in result


def test_relative_date_3_weeks_ago():
    result = relative_date(_ago(86400 * 21))
    assert "week" in result


# ---------------------------------------------------------------------------
# relative_date — months
# ---------------------------------------------------------------------------


def test_relative_date_1_month_ago():
    result = relative_date(_ago(86400 * 35))  # ~35 days, < 60
    assert "1 month" in result


def test_relative_date_several_months_ago():
    result = relative_date(_ago(86400 * 120))  # ~4 months
    assert "month" in result


# ---------------------------------------------------------------------------
# relative_date — years (falls back to full date)
# ---------------------------------------------------------------------------


def test_relative_date_1_year_ago():
    result = relative_date(_ago(86400 * 400))  # ~13 months
    # Falls back to full formatted date for 1+ year
    assert isinstance(result, str)
    assert len(result) > 0


def test_relative_date_multiple_years_ago():
    result = relative_date(_ago(86400 * 800))  # > 2 years
    # Falls back to full formatted date
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# relative_date — future date falls back to formatted date
# ---------------------------------------------------------------------------


def test_relative_date_future_returns_formatted():
    future = UTCDatetime(_now() + timedelta(days=1))
    result = relative_date(future)
    # For future dates, relative_date returns format_datetime output
    assert isinstance(result, str)
    assert len(result) > 0
