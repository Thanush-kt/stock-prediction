"""Prediction and timestamp validation for signal execution.

Validates that predictions are not stale, future-dated, missing timestamps,
or incompatible with the requested model version before generating orders.
"""
from __future__ import annotations

import datetime as dt
from typing import Any
import zoneinfo

import pandas as pd

from packages.shared.config import get_settings
from packages.shared.logging import get_logger

log = get_logger(__name__)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")


def get_nyse_holidays(year: int) -> set[dt.date]:
    """Return official NYSE market holiday dates for a given year."""
    holidays: set[dt.date] = set()

    def add_observed(d: dt.date) -> None:
        if d.weekday() == 5:  # Saturday -> Friday
            holidays.add(d - dt.timedelta(days=1))
        elif d.weekday() == 6:  # Sunday -> Monday
            holidays.add(d + dt.timedelta(days=1))
        else:
            holidays.add(d)

    # New Year's Day (Jan 1)
    add_observed(dt.date(year, 1, 1))

    # Martin Luther King Jr. Day (3rd Monday of Jan)
    d = dt.date(year, 1, 1)
    d += dt.timedelta(days=(0 - d.weekday() + 7) % 7) + dt.timedelta(weeks=2)
    holidays.add(d)

    # Presidents' Day / Washington's Birthday (3rd Monday of Feb)
    d = dt.date(year, 2, 1)
    d += dt.timedelta(days=(0 - d.weekday() + 7) % 7) + dt.timedelta(weeks=2)
    holidays.add(d)

    # Good Friday (2 days before Easter Sunday via anonymous Gregorian algorithm)
    a, b, c = year % 19, year // 100, year % 100
    d_val, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_val - g + 15) % 30
    i, k = c // 4, c % 4
    l_val = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_val) // 451
    month = (h + l_val - 7 * m + 114) // 31
    day = ((h + l_val - 7 * m + 114) % 31) + 1
    easter = dt.date(year, month, day)
    holidays.add(easter - dt.timedelta(days=2))

    # Memorial Day (Last Monday of May)
    d = dt.date(year, 5, 31)
    d -= dt.timedelta(days=(d.weekday() - 0) % 7)
    holidays.add(d)

    # Juneteenth National Independence Day (June 19)
    add_observed(dt.date(year, 6, 19))

    # Independence Day (July 4)
    add_observed(dt.date(year, 7, 4))

    # Labor Day (1st Monday of Sep)
    d = dt.date(year, 9, 1)
    d += dt.timedelta(days=(0 - d.weekday() + 7) % 7)
    holidays.add(d)

    # Thanksgiving Day (4th Thursday of Nov)
    d = dt.date(year, 11, 1)
    d += dt.timedelta(days=(3 - d.weekday() + 7) % 7) + dt.timedelta(weeks=3)
    holidays.add(d)

    # Christmas Day (Dec 25)
    add_observed(dt.date(year, 12, 25))

    return holidays


def is_trading_day(d: dt.date) -> bool:
    """Return True if the date is a normal weekday and not an NYSE market holiday."""
    if d.weekday() >= 5:
        return False
    return d not in get_nyse_holidays(d.year)


def trading_days_between(start_date: dt.date, end_date: dt.date) -> int:
    """Count market trading days in the half-open interval (start_date, end_date]."""
    if end_date <= start_date:
        return 0
    cur = start_date + dt.timedelta(days=1)
    count = 0
    while cur <= end_date:
        if is_trading_day(cur):
            count += 1
        cur += dt.timedelta(days=1)
    return count


def _coerce_to_utc_datetime(ts: Any) -> dt.datetime | None:
    """Safely convert supported timestamp types to a timezone-aware UTC datetime."""
    if ts is None or pd.isna(ts):
        return None
    if isinstance(ts, pd.Timestamp):
        ts_dt = ts.to_pydatetime()
    elif isinstance(ts, dt.datetime):
        ts_dt = ts
    elif isinstance(ts, dt.date):
        ts_dt = dt.datetime.combine(ts, dt.time(16, 0))
    else:
        return None

    if ts_dt.tzinfo is None:
        return ts_dt.replace(tzinfo=dt.timezone.utc)
    return ts_dt.astimezone(dt.timezone.utc)


def validate_prediction(  # pylint: disable=too-many-arguments,too-many-locals,too-many-return-statements
    *,
    symbol: str,
    ts: Any,
    pred_model_version: str | None,
    expected_model_version: str,
    as_of: dt.datetime,
    max_age_days: int | None = None,
    max_trading_days: int | None = None,
) -> tuple[bool, str | None]:
    """Validate prediction timestamp and model version before order generation.

    Returns:
        (is_valid, failure_reason)
    """
    # 1. Model version checks
    if not expected_model_version or not str(expected_model_version).strip():
        return False, f"{symbol}: invalid_model_version: expected_model_version cannot be empty"

    if pred_model_version is not None and pred_model_version != expected_model_version:
        return False, (
            f"{symbol}: model_version_mismatch: got {pred_model_version!r}, "
            f"expected {expected_model_version!r}"
        )

    # 2. Timestamp presence checks
    ts_dt = _coerce_to_utc_datetime(ts)
    if ts_dt is None:
        return False, f"{symbol}: missing_timestamp: prediction ts {ts!r} is missing or invalid"

    as_of_dt = (
        as_of.replace(tzinfo=dt.timezone.utc)
        if as_of.tzinfo is None
        else as_of.astimezone(dt.timezone.utc)
    )

    # 3. Future-dated check (allow 60s tolerance for minor clock skew)
    if ts_dt > as_of_dt + dt.timedelta(seconds=60):
        return False, (
            f"{symbol}: future_dated_prediction: ts {ts_dt.isoformat()} is after "
            f"as_of {as_of_dt.isoformat()}"
        )

    # 4. Staleness check
    settings = get_settings()
    effective_max_age_days = (
        max_age_days if max_age_days is not None else settings.max_prediction_age_days
    )
    effective_max_trading_days = (
        max_trading_days
        if max_trading_days is not None
        else settings.max_prediction_trading_days
    )

    pred_ny_date = ts_dt.astimezone(NY_TZ).date()
    as_of_ny_date = as_of_dt.astimezone(NY_TZ).date()

    calendar_days = (as_of_ny_date - pred_ny_date).days
    trading_days = trading_days_between(pred_ny_date, as_of_ny_date)

    if effective_max_trading_days is not None and trading_days > effective_max_trading_days:
        return False, (
            f"{symbol}: stale_prediction: elapsed trading days ({trading_days}) exceeds max "
            f"allowed ({effective_max_trading_days}) [calendar_days={calendar_days}]"
        )

    if effective_max_age_days is not None and calendar_days > effective_max_age_days:
        if trading_days > effective_max_trading_days or calendar_days > (effective_max_age_days + 4):
            return False, (
                f"{symbol}: stale_prediction: elapsed calendar days ({calendar_days}) exceeds max "
                f"allowed ({effective_max_age_days})"
            )

    return True, None
