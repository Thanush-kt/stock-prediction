"""Indicator engine tests — deterministic price series, sanity bounds on indicators."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from packages.shared.models import Indicator, Ticker
from services.ingestion import features


@pytest.fixture(name="long_bars")
def fixture_long_bars() -> pd.DataFrame:
    n = 250
    idx = pd.date_range("2023-01-02", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0.1, 1.0, n))
    open_ = close + rng.normal(0, 0.3, n)
    high = np.maximum(close, open_) + rng.uniform(0.1, 1.0, n)
    low = np.minimum(close, open_) - rng.uniform(0.1, 1.0, n)
    volume = rng.uniform(1e6, 5e6, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def test_compute_indicators_produces_expected_columns(long_bars):
    ind = features.compute_indicators(long_bars)
    expected = {
        "rsi_14",
        "macd",
        "macd_hist",
        "macd_signal",
        "bb_lower",
        "bb_mid",
        "bb_upper",
        "sma_20",
        "sma_50",
        "sma_200",
        "ema_12",
        "ema_26",
    }
    assert expected.issubset(set(ind.columns))


def test_rsi_in_valid_range(long_bars):
    ind = features.compute_indicators(long_bars)
    rsi = ind["rsi_14"].dropna()
    assert len(rsi) > 0
    assert ((rsi >= 0) & (rsi <= 100)).all()


def test_bollinger_ordering(long_bars):
    ind = features.compute_indicators(long_bars).dropna()
    assert (ind["bb_lower"] <= ind["bb_mid"]).all()
    assert (ind["bb_mid"] <= ind["bb_upper"]).all()


def test_upsert_indicators_idempotent_and_skips_nan(session, long_bars):
    session.add(Ticker(symbol="AAPL", active=True))
    session.flush()

    ind = features.compute_indicators(long_bars)
    n1 = features.upsert_indicators(session, "AAPL", ind)
    session.flush()
    n2 = features.upsert_indicators(session, "AAPL", ind)
    session.flush()

    assert n1 > 0
    assert n2 == 0

    rows = session.execute(select(Indicator).where(Indicator.symbol == "AAPL")).all()
    values = [r[0].value for r in rows]
    assert all(not np.isnan(v) for v in values)


def test_load_bars_excludes_invalid_bars(session, caplog):
    session.add(Ticker(symbol="AAPL", active=True))
    session.flush()

    from packages.shared.models import PriceBar
    import datetime as dt

    ts1 = dt.datetime(2024, 1, 2, 4, 0, tzinfo=dt.timezone.utc)
    ts2 = dt.datetime(2024, 1, 3, 4, 0, tzinfo=dt.timezone.utc)
    ts_bad = dt.datetime(2024, 1, 4, 4, 0, tzinfo=dt.timezone.utc)

    # In SQLite, test invalid bar with OHLC inconsistency (high < low)
    session.add_all([
        PriceBar(symbol="AAPL", ts=ts1, open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0, source="test"),
        PriceBar(symbol="AAPL", ts=ts2, open=102.0, high=107.0, low=98.0, close=105.0, volume=1200.0, source="test"),
        PriceBar(symbol="AAPL", ts=ts_bad, open=105.0, high=90.0, low=100.0, close=95.0, volume=1500.0, source="test"),
    ])
    session.flush()

    with caplog.at_level("WARNING"):
        bars = features.load_bars(session, "AAPL")

    assert len(bars) == 2
    assert "Rejected 1 invalid OHLCV row(s) for symbol AAPL" in caplog.text
    assert ts_bad not in bars.index


def test_compute_indicators_excludes_invalid_rows(long_bars):
    corrupt = long_bars.copy()
    # corrupt row at index 50 with NaN close
    corrupt.iloc[50, corrupt.columns.get_loc("close")] = float("nan")
    # corrupt row at index 100 with high < low
    corrupt.iloc[100, corrupt.columns.get_loc("high")] = 10.0
    corrupt.iloc[100, corrupt.columns.get_loc("low")] = 50.0

    ind = features.compute_indicators(corrupt)
    assert len(ind) == len(long_bars) - 2
    assert corrupt.index[50] not in ind.index
    assert corrupt.index[100] not in ind.index


def test_latest_invalid_bar_does_not_contaminate_indicators(session, long_bars):
    session.add(Ticker(symbol="AAPL", active=True))
    session.flush()

    # Save valid bars plus 1 latest invalid bar to database
    from packages.shared.models import PriceBar
    bars = []
    for ts, row in long_bars.iterrows():
        bars.append(PriceBar(
            symbol="AAPL",
            ts=ts.to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            source="test",
        ))
    latest_ts = long_bars.index[-1] + pd.Timedelta(days=1)
    bars.append(PriceBar(
        symbol="AAPL",
        ts=latest_ts.to_pydatetime(),
        open=150.0,
        high=90.0,
        low=155.0,  # Invalid OHLC bar (high < low)
        close=100.0,
        volume=2000000.0,
        source="test",
    ))
    session.add_all(bars)
    session.flush()

    # Compute indicators for symbol
    inserted = features.compute_for_symbol(session, "AAPL")
    assert inserted > 0

    # Ensure NO indicator rows exist for latest_ts
    ind_latest = session.execute(
        select(Indicator).where(Indicator.symbol == "AAPL", Indicator.ts == latest_ts.to_pydatetime())
    ).scalars().all()
    assert len(ind_latest) == 0

