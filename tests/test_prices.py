"""Price ingestion tests — yfinance mocked, idempotent upsert verified."""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest
from sqlalchemy import select

from packages.shared.models import PriceBar, Ticker
from services.ingestion import prices


@pytest.fixture(name="fake_ohlcv")
def fixture_fake_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=5, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100.0, 101, 102, 103, 104],
            "High": [101.0, 102, 103, 104, 105],
            "Low": [99.0, 100, 101, 102, 103],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "Volume": [1000.0, 1100, 1200, 1300, 1400],
        },
        index=idx,
    )


def test_fetch_ohlcv_normalizes_columns(monkeypatch, fake_ohlcv):
    class FakeTicker:
        def __init__(self, _):
            pass

        def history(self, **_kwargs):
            return fake_ohlcv

    monkeypatch.setattr(prices.yf, "Ticker", FakeTicker)

    df = prices.fetch_ohlcv("AAPL", dt.date(2024, 1, 1))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 5
    assert str(df.index.tz) == "UTC"


def test_upsert_bars_is_idempotent(session, fake_ohlcv):
    df = fake_ohlcv.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )[["open", "high", "low", "close", "volume"]]

    inserted_first = prices.upsert_bars(session, "AAPL", df)
    session.flush()
    inserted_second = prices.upsert_bars(session, "AAPL", df)
    session.flush()

    assert inserted_first == 5
    assert inserted_second == 0

    total = session.execute(select(PriceBar).where(PriceBar.symbol == "AAPL")).all()
    assert len(total) == 5

    ticker = session.execute(select(Ticker).where(Ticker.symbol == "AAPL")).scalar_one()
    assert ticker.active is True


def test_upsert_bars_empty_df_noop(session):
    n = prices.upsert_bars(session, "AAPL", pd.DataFrame())
    assert n == 0


def test_validate_bars_filters_nan_and_inf(caplog):
    idx = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [float("nan"), 100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [105.0, float("inf"), 105.0, 105.0, 105.0, 105.0],
            "low": [95.0, 95.0, float("-inf"), 95.0, 95.0, 95.0],
            "close": [102.0, 102.0, 102.0, float("nan"), 102.0, 102.0],
            "volume": [1000.0, 1000.0, 1000.0, 1000.0, float("nan"), 1000.0],
        },
        index=idx,
    )
    with caplog.at_level("WARNING"):
        cleaned = prices.validate_bars(df, symbol="AAPL")
    assert len(cleaned) == 1
    assert "Rejected 5 invalid OHLCV row(s) for symbol AAPL" in caplog.text
    assert cleaned.iloc[0]["open"] == 100.0
    assert cleaned.iloc[0]["close"] == 102.0


def test_validate_bars_filters_invalid_prices_and_negative_volume():
    idx = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 0.0, -10.0, 100.0, 100.0, 100.0],
            "high": [105.0, 105.0, 105.0, 0.0, 105.0, 105.0],
            "low": [95.0, 95.0, 95.0, 95.0, -1.0, 95.0],
            "close": [102.0, 102.0, 102.0, 102.0, 102.0, 0.0],
            "volume": [0.0, 1000.0, 1000.0, 1000.0, 1000.0, -50.0],  # volume=0 is valid
        },
        index=idx,
    )
    cleaned = prices.validate_bars(df, symbol="AAPL")
    # Only the first row (open=100, high=105, low=95, close=102, volume=0) is valid
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["open"] == 100.0
    assert cleaned.iloc[0]["volume"] == 0.0


def test_validate_bars_filters_ohlc_inconsistencies():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 110.0, 90.0, 100.0, 100.0],
            "high": [90.0, 105.0, 105.0, 105.0, 105.0],  # row 0: high < low & high < open
            "low": [95.0, 95.0, 95.0, 95.0, 103.0],      # row 4: low > open & low > close
            "close": [98.0, 100.0, 110.0, 90.0, 101.0],  # row 2: close > high; row 3: close < low
            "volume": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
        },
        index=idx,
    )
    cleaned = prices.validate_bars(df, symbol="AAPL")
    assert len(cleaned) == 0


def test_validate_bars_preserves_valid_rows():
    idx = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [100.0, 102.0],
            "high": [105.0, 106.0],
            "low": [98.0, 100.0],
            "close": [103.0, 104.0],
            "volume": [500000.0, 600000.0],
        },
        index=idx,
    )
    cleaned = prices.validate_bars(df, symbol="AAPL")
    assert len(cleaned) == 2
    pd.testing.assert_frame_equal(cleaned, df)


def test_fetch_ohlcv_rejects_corrupted_rows(monkeypatch, caplog):
    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    corrupt_df = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [95.0, 96.0, 97.0],
            "Close": [102.0, float("nan"), 104.0],  # middle row has NaN close
            "Volume": [1000.0, 1000.0, 1000.0],
        },
        index=idx,
    )

    class FakeTicker:
        def __init__(self, _):
            pass

        def history(self, **_kwargs):
            return corrupt_df

    monkeypatch.setattr(prices.yf, "Ticker", FakeTicker)

    with caplog.at_level("WARNING"):
        df = prices.fetch_ohlcv("AAPL", dt.date(2024, 1, 1))

    assert len(df) == 2
    assert "Rejected 1 invalid OHLCV row(s) for symbol AAPL" in caplog.text
    assert list(df.index) == [idx[0], idx[2]]


def test_upsert_bars_rejects_invalid_rows(session):
    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    mixed_df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 90.0, 107.0],  # row 1: high < low
            "low": [95.0, 96.0, 97.0],
            "close": [102.0, 103.0, float("nan")],  # row 2: NaN close
            "volume": [1000.0, 1000.0, 1000.0],
        },
        index=idx,
    )
    inserted = prices.upsert_bars(session, "AAPL", mixed_df)
    session.flush()

    assert inserted == 1
    bars = session.execute(select(PriceBar).where(PriceBar.symbol == "AAPL")).scalars().all()
    assert len(bars) == 1
    assert bars[0].open == 100.0
    assert bars[0].close == 102.0

