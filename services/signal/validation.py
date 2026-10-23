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


def get_nse_holidays(year: int) -> set[dt.date]:
    """Return official/standard NSE India market holiday dates for a given year."""
    holidays: set[dt.date] = {
        dt.date(year, 1, 26),   # Republic Day
        dt.date(year, 8, 15),   # Independence Day
        dt.date(year, 10, 2),   # Mahatma Gandhi Jayanti
        dt.date(year, 12, 25),  # Christmas
    }
    # Year-specific variable festivals (official NSE calendar)
    if year == 2024:
        holidays.update({
            dt.date(2024, 1, 22), dt.date(2024, 3, 8), dt.date(2024, 3, 25),
            dt.date(2024, 3, 29), dt.date(2024, 4, 11), dt.date(2024, 4, 17),
            dt.date(2024, 5, 1), dt.date(2024, 5, 20), dt.date(2024, 6, 17),
            dt.date(2024, 7, 17), dt.date(2024, 11, 1), dt.date(2024, 11, 15),
            dt.date(2024, 11, 20),
        })
    elif year == 2025:
        holidays.update({
            dt.date(2025, 2, 26), dt.date(2025, 3, 14), dt.date(2025, 3, 31),
            dt.date(2025, 4, 10), dt.date(2025, 4, 14), dt.date(2025, 4, 18),
            dt.date(2025, 5, 1), dt.date(2025, 6, 7), dt.date(2025, 8, 27),
            dt.date(2025, 10, 21), dt.date(2025, 10, 22), dt.date(2025, 11, 5),
        })
    elif year == 2026:
        holidays.update({
            dt.date(2026, 3, 15), dt.date(2026, 3, 20), dt.date(2026, 4, 3),
            dt.date(2026, 4, 14), dt.date(2026, 5, 1), dt.date(2026, 5, 27),
            dt.date(2026, 6, 26), dt.date(2026, 9, 15), dt.date(2026, 10, 20),
            dt.date(2026, 11, 8), dt.date(2026, 11, 24),
        })
    return holidays


def exchange_for_symbol(symbol: str) -> str:
    """Classify the exchange / market segment from the symbol format.

    Returns "NSE" for Indian stocks (.NS, .BO), "CRYPTO" for -USD pairs,
    "COMMODITY" for =F futures, and "NYSE" for standard US equities.
    """
    sym = symbol.upper()
    if sym.endswith(".NS") or sym.endswith(".BO"):
        return "NSE"
    if sym.endswith("-USD") or "-USD" in sym:
        return "CRYPTO"
    if sym.endswith("=F"):
        return "COMMODITY"
    return "NYSE"


def exchange_timezone(exchange: str) -> zoneinfo.ZoneInfo:
    """Return the primary timezone for the given exchange."""
    if exchange == "NSE":
        return zoneinfo.ZoneInfo("Asia/Kolkata")
    if exchange == "CRYPTO":
        return zoneinfo.ZoneInfo("UTC")
    if exchange == "COMMODITY":
        return zoneinfo.ZoneInfo("America/Chicago")
    return zoneinfo.ZoneInfo("America/New_York")


def is_trading_day(d: dt.date, exchange: str = "NYSE") -> bool:
    """Return True if the date is a normal trading day for the given exchange.

    - Weekends (Sat/Sun) are non-trading for all equity/commodity markets.
    - NYSE checks official NYSE holiday list.
    - NSE checks official NSE holiday list.
    - Crypto operates 24/7 (weekends included).
    - Other equities/commodities default to weekday-only without NYSE-specific holidays.
    """
    if exchange == "CRYPTO":
        return True
    if d.weekday() >= 5:
        return False
    if exchange == "NYSE":
        return d not in get_nyse_holidays(d.year)
    if exchange == "NSE":
        return d not in get_nse_holidays(d.year)
    return True


def get_exchange_local_date(ts: dt.datetime | dt.date | Any, exchange: str = "NYSE") -> dt.date:
    """Convert ts into the exchange's local date."""
    if isinstance(ts, dt.date) and not isinstance(ts, dt.datetime):
        return ts
    tz = exchange_timezone(exchange)
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if not isinstance(ts, dt.datetime):
        ts = dt.datetime.combine(ts, dt.time.min)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(tz).date()


def get_next_trading_session_date(d: dt.date, exchange: str = "NYSE") -> dt.date:
    """Return the next trading day strictly after d for the given exchange."""
    cur = d + dt.timedelta(days=1)
    while not is_trading_day(cur, exchange=exchange):
        cur += dt.timedelta(days=1)
    return cur


def get_previous_trading_session_date(d: dt.date, exchange: str = "NYSE") -> dt.date:
    """Return the nearest trading day strictly before d for the given exchange."""
    cur = d - dt.timedelta(days=1)
    while not is_trading_day(cur, exchange=exchange):
        cur -= dt.timedelta(days=1)
    return cur


def get_current_trading_session(exchange: str = "NYSE", as_of: dt.datetime | None = None) -> dt.date:
    """Return the trading session date corresponding to as_of (defaults to now).

    If as_of lands on a trading day:
      - Returns that day's date.
    If as_of lands on a weekend/holiday:
      - Returns the previous completed trading day.
    """
    tz = exchange_timezone(exchange)
    now_utc = as_of or dt.datetime.now(dt.timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=dt.timezone.utc)
    now_local = now_utc.astimezone(tz)
    local_date = now_local.date()
    if is_trading_day(local_date, exchange=exchange):
        return local_date
    return get_previous_trading_session_date(local_date, exchange=exchange)


def is_market_session_open(exchange: str = "NYSE", as_of: dt.datetime | None = None) -> bool:
    """Check if the market is currently open for regular trading hours."""
    if exchange == "CRYPTO":
        return True
    tz = exchange_timezone(exchange)
    now_utc = as_of or dt.datetime.now(dt.timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=dt.timezone.utc)
    now_local = now_utc.astimezone(tz)
    local_date = now_local.date()
    if not is_trading_day(local_date, exchange=exchange):
        return False
    local_time = now_local.time()
    if exchange == "NYSE":
        return dt.time(9, 30) <= local_time <= dt.time(16, 0)
    if exchange == "NSE":
        return dt.time(9, 15) <= local_time <= dt.time(15, 30)
    if exchange == "COMMODITY":
        return dt.time(9, 30) <= local_time <= dt.time(17, 0)
    return False


def trading_days_between(start_date: dt.date, end_date: dt.date, exchange: str = "NYSE") -> int:
    """Count market trading days in the half-open interval (start_date, end_date]."""
    if end_date <= start_date:
        return 0
    cur = start_date + dt.timedelta(days=1)
    count = 0
    while cur <= end_date:
        if is_trading_day(cur, exchange=exchange):
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
    exch = exchange_for_symbol(symbol)
    trading_days = (
        calendar_days
        if exch == "CRYPTO"
        else trading_days_between(pred_ny_date, as_of_ny_date, exchange=exch)
    )

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
