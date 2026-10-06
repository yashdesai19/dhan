"""Calendar periods in the user's local time zone.

A transaction belongs to the day and month on the user's wall clock, not UTC's: ₹500 spent at
00:30 IST on 1 October is October spending even though it is still 30 September in UTC.
Periods are therefore built from local midnights and returned as aware datetimes, which
compare correctly against timestamptz columns whatever the database session's time zone.
Every range is half-open: start <= instant < end.
"""

import calendar
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi_app.core.config import settings

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def get_timezone(name: str | None = None) -> ZoneInfo:
    """ZoneInfo for an IANA name such as 'Asia/Kolkata' (default: settings.DEFAULT_TIMEZONE)."""
    key = name or settings.DEFAULT_TIMEZONE
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown time zone: {key!r}") from exc


def parse_month(month: str) -> tuple[int, int]:
    """'2026-09' -> (2026, 9). ValueError for anything that isn't a usable calendar month."""
    try:
        year_part, month_part = month.split("-")
        year, mon = int(year_part), int(month_part)
    except ValueError as exc:
        raise ValueError(f"Month must look like YYYY-MM, got {month!r}") from exc
    if not (1 <= year <= 9998 and 1 <= mon <= 12):
        raise ValueError(f"Month out of range: {month!r}")
    return year, mon


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Moves a (year, month) pair by delta months, across year boundaries."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def local_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz)


def month_bounds(year: int, month: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """[local midnight on the 1st, local midnight on the 1st of the next month)."""
    next_year, next_month = shift_month(year, month, 1)
    return (
        local_midnight(date(year, month, 1), tz),
        local_midnight(date(next_year, next_month, 1), tz),
    )


def days_bounds(first: date, last: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Instants covering the local days first..last, both inclusive."""
    return local_midnight(first, tz), local_midnight(last + timedelta(days=1), tz)


def assume_local(instant: datetime) -> datetime:
    """Gives a timestamp sent without an offset the DHAN time zone (what the user's clock read).

    Left naive, the database driver would apply the server machine's own zone, so the stored
    instant would depend on where the API happens to run.
    """
    if instant.tzinfo is None:
        return instant.replace(tzinfo=get_timezone())
    return instant


def local_date(instant: datetime, tz: ZoneInfo) -> date:
    """The user's calendar date for a stored instant (a naive value is taken as UTC)."""
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(tz).date()


def today_in(tz: ZoneInfo) -> date:
    return datetime.now(tz).date()
