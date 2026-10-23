"""Unit tests for prediction timestamp and staleness validation."""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from services.signal.validation import (
    exchange_for_symbol,
    exchange_timezone,
    get_current_trading_session,
    get_exchange_local_date,
    get_next_trading_session_date,
    get_nse_holidays,
    get_nyse_holidays,
    get_previous_trading_session_date,
    is_market_session_open,
    is_trading_day,
    trading_days_between,
    validate_prediction,
)


def test_nyse_holidays_contains_major_holidays_for_2024():
    holidays = get_nyse_holidays(2024)
    assert dt.date(2024, 1, 1) in holidays  # New Year
    assert dt.date(2024, 1, 15) in holidays  # MLK
    assert dt.date(2024, 2, 19) in holidays  # Presidents
    assert dt.date(2024, 3, 29) in holidays  # Good Friday
    assert dt.date(2024, 5, 27) in holidays  # Memorial Day
    assert dt.date(2024, 6, 19) in holidays  # Juneteenth
    assert dt.date(2024, 7, 4) in holidays  # July 4
    assert dt.date(2024, 9, 2) in holidays  # Labor Day
    assert dt.date(2024, 11, 28) in holidays  # Thanksgiving
    assert dt.date(2024, 12, 25) in holidays  # Christmas


def test_is_trading_day_weekend_and_holidays():
    assert is_trading_day(dt.date(2024, 5, 1)) is True  # Wednesday
    assert is_trading_day(dt.date(2024, 5, 4)) is False  # Saturday
    assert is_trading_day(dt.date(2024, 5, 5)) is False  # Sunday
    assert is_trading_day(dt.date(2024, 5, 27)) is False  # Memorial Day


def test_trading_days_between_weekend_and_holidays():
    # Friday 2024-05-03 to Monday 2024-05-06 is 1 trading day
    assert trading_days_between(dt.date(2024, 5, 3), dt.date(2024, 5, 6)) == 1
    # Friday 2024-05-03 to Sunday 2024-05-05 is 0 trading days
    assert trading_days_between(dt.date(2024, 5, 3), dt.date(2024, 5, 5)) == 0
    # Friday 2024-05-24 to Tuesday 2024-05-28 (Memorial Day on Monday) is 1 trading day
    assert trading_days_between(dt.date(2024, 5, 24), dt.date(2024, 5, 28)) == 1
    # Normal Mon to Wed is 2 trading days
    assert trading_days_between(dt.date(2024, 5, 6), dt.date(2024, 5, 8)) == 2
    # End before or equal to start is 0
    assert trading_days_between(dt.date(2024, 5, 6), dt.date(2024, 5, 6)) == 0
    assert trading_days_between(dt.date(2024, 5, 8), dt.date(2024, 5, 6)) == 0


def test_validate_prediction_valid_fresh():
    as_of = dt.datetime(2024, 5, 1, 16, 30, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
    )
    assert ok is True
    assert err is None


def test_validate_prediction_valid_over_weekend():
    # Friday 16:00 ET evaluated Monday 09:30 ET
    as_of = dt.datetime(2024, 5, 6, 13, 30, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 3, 20, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
        max_trading_days=1,
    )
    assert ok is True
    assert err is None


def test_validate_prediction_valid_over_holiday_weekend():
    # Friday 16:00 ET evaluated Tuesday 09:30 ET after Memorial Day
    as_of = dt.datetime(2024, 5, 28, 13, 30, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 24, 20, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
        max_trading_days=1,
    )
    assert ok is True
    assert err is None


def test_validate_prediction_rejects_missing_or_nat_ts():
    as_of = dt.datetime(2024, 5, 1, 16, 30, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=None,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
    )
    assert ok is False
    assert "missing_timestamp" in str(err)

    ok, err = validate_prediction(
        symbol="AAPL",
        ts=pd.NaT,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
    )
    assert ok is False
    assert "missing_timestamp" in str(err)


def test_validate_prediction_rejects_future_dated():
    as_of = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    future_ts = dt.datetime(2024, 5, 2, 16, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=future_ts,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
    )
    assert ok is False
    assert "future_dated_prediction" in str(err)


def test_validate_prediction_rejects_model_version_mismatch():
    as_of = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v2",
        expected_model_version="v1",
        as_of=as_of,
    )
    assert ok is False
    assert "model_version_mismatch" in str(err)


def test_validate_prediction_rejects_empty_expected_model_version():
    as_of = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v1",
        expected_model_version="",
        as_of=as_of,
    )
    assert ok is False
    assert "invalid_model_version" in str(err)


def test_validate_prediction_rejects_stale_trading_days():
    # Friday evaluated Wednesday in a normal week (2 trading days elapsed)
    as_of = dt.datetime(2024, 5, 8, 16, 0, tzinfo=dt.timezone.utc)
    ts = dt.datetime(2024, 5, 3, 20, 0, tzinfo=dt.timezone.utc)
    ok, err = validate_prediction(
        symbol="AAPL",
        ts=ts,
        pred_model_version="v1",
        expected_model_version="v1",
        as_of=as_of,
        max_trading_days=1,
    )
    assert ok is False
    assert "stale_prediction" in str(err)
    assert "elapsed trading days (3) exceeds max allowed (1)" in str(err)


def test_nse_holidays_and_trading_days():
    nse_hols = get_nse_holidays(2024)
    assert dt.date(2024, 1, 26) in nse_hols  # Republic Day
    assert dt.date(2024, 8, 15) in nse_hols  # Independence Day
    assert dt.date(2024, 10, 2) in nse_hols  # Gandhi Jayanti
    assert dt.date(2024, 12, 25) in nse_hols  # Christmas

    assert is_trading_day(dt.date(2024, 1, 26), exchange="NSE") is False
    assert is_trading_day(dt.date(2024, 5, 1), exchange="NSE") is False  # Maharashtra Day
    assert is_trading_day(dt.date(2024, 5, 2), exchange="NSE") is True   # Thursday


def test_exchange_for_symbol_classification():
    assert exchange_for_symbol("AAPL") == "NYSE"
    assert exchange_for_symbol("MSFT") == "NYSE"
    assert exchange_for_symbol("RELIANCE.NS") == "NSE"
    assert exchange_for_symbol("TCS.BO") == "NSE"
    assert exchange_for_symbol("BTC-USD") == "CRYPTO"
    assert exchange_for_symbol("GC=F") == "COMMODITY"


def test_exchange_timezone():
    assert str(exchange_timezone("NYSE")) == "America/New_York"
    assert str(exchange_timezone("NSE")) == "Asia/Kolkata"
    assert str(exchange_timezone("CRYPTO")) == "UTC"


def test_get_exchange_local_date():
    # Indian bar at 18:30 UTC on Oct 15 is Oct 16 in IST
    ts_utc = dt.datetime(2026, 10, 15, 18, 30, tzinfo=dt.timezone.utc)
    local_d = get_exchange_local_date(ts_utc, exchange="NSE")
    assert local_d == dt.date(2026, 10, 16)

    # US bar at 04:00 UTC on Oct 21 is Oct 21 (or prior evening)
    ts_us = dt.datetime(2026, 10, 21, 4, 0, tzinfo=dt.timezone.utc)
    local_us = get_exchange_local_date(ts_us, exchange="NYSE")
    assert local_us == dt.date(2026, 10, 21)


def test_get_next_trading_session_date():
    # Friday to Monday
    fri = dt.date(2024, 5, 3)
    next_d = get_next_trading_session_date(fri, exchange="NYSE")
    assert next_d == dt.date(2024, 5, 6)

    # Over holiday (Memorial Day on Monday 2024-05-27)
    fri_holiday = dt.date(2024, 5, 24)
    next_post_holiday = get_next_trading_session_date(fri_holiday, exchange="NYSE")
    assert next_post_holiday == dt.date(2024, 5, 28)

    # Crypto (24/7) Friday to Saturday
    next_crypto = get_next_trading_session_date(fri, exchange="CRYPTO")
    assert next_crypto == dt.date(2024, 5, 4)


def test_get_current_trading_session():
    # Wednesday during trading day
    wed = dt.datetime(2024, 5, 1, 14, 0, tzinfo=dt.timezone.utc)
    assert get_current_trading_session("NYSE", as_of=wed) == dt.date(2024, 5, 1)

    # Saturday returns Friday
    sat = dt.datetime(2024, 5, 4, 12, 0, tzinfo=dt.timezone.utc)
    assert get_current_trading_session("NYSE", as_of=sat) == dt.date(2024, 5, 3)


def test_is_market_session_open():
    # NYSE 10:00 AM ET on Wednesday 2024-05-01 is 14:00 UTC
    open_time = dt.datetime(2024, 5, 1, 14, 0, tzinfo=dt.timezone.utc)
    assert is_market_session_open("NYSE", as_of=open_time) is True

    # NYSE 05:00 AM ET on Wednesday 2024-05-01 is 09:00 UTC (pre-market)
    pre_time = dt.datetime(2024, 5, 1, 9, 0, tzinfo=dt.timezone.utc)
    assert is_market_session_open("NYSE", as_of=pre_time) is False

    # Crypto is always open
    assert is_market_session_open("CRYPTO", as_of=pre_time) is True

