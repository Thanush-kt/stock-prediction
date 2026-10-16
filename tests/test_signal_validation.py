"""Unit tests for prediction timestamp and staleness validation."""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from services.signal.validation import (
    get_nyse_holidays,
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
