"""OHLCV price ingestion via yfinance."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.shared.db import upsert_ignore
from packages.shared.logging import get_logger
from packages.shared.models import PriceBar, Ticker

log = get_logger(__name__)


def validate_ticker(symbol: str) -> None:
    """Validate that *symbol* exists on yfinance. Raises ValueError if invalid."""
    ticker = yf.Ticker(symbol)
    try:
        fast = ticker.fast_info
        price = getattr(fast, "last_price", None)
        if price is None or price != price:  # None or NaN
            raise ValueError(f"Symbol '{symbol}' not found or has no price data")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Symbol '{symbol}' validation failed: {exc}") from exc


def validate_bars(df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """Filter out rows with NaN, infinite, non-positive prices, negative volume,
    or OHLC inconsistencies (high < low, high < open, high < close, low > open, low > close).

    Logs a warning if any rows are dropped.
    """
    if df.empty:
        return df

    required_cols = ["open", "high", "low", "close", "volume"]
    if not all(col in df.columns for col in required_cols):
        return df

    # Coerce to numeric in case any column has object/string type
    numeric_df = df[required_cols].apply(pd.to_numeric, errors="coerce")

    # Check finite, positive prices, non-negative volume, and OHLC consistency
    valid = (
        np.isfinite(numeric_df["open"]) & (numeric_df["open"] > 0)
        & np.isfinite(numeric_df["high"]) & (numeric_df["high"] > 0)
        & np.isfinite(numeric_df["low"]) & (numeric_df["low"] > 0)
        & np.isfinite(numeric_df["close"]) & (numeric_df["close"] > 0)
        & np.isfinite(numeric_df["volume"]) & (numeric_df["volume"] >= 0)
        & (numeric_df["high"] >= numeric_df["low"])
        & (numeric_df["high"] >= numeric_df["open"])
        & (numeric_df["high"] >= numeric_df["close"])
        & (numeric_df["low"] <= numeric_df["open"])
        & (numeric_df["low"] <= numeric_df["close"])
    )

    rejected_count = int((~valid).sum())
    if rejected_count > 0:
        log.warning(
            "Rejected %d invalid OHLCV row(s) for symbol %s (NaN/Inf, non-positive price, negative volume, or OHLC inconsistency)",
            rejected_count,
            symbol or "unknown",
        )

    return df[valid].copy()


def fetch_ohlcv(symbol: str, start: dt.date, end: dt.date | None = None) -> pd.DataFrame:
    """Pull daily OHLCV bars from yfinance. Returns DataFrame indexed by tz-aware UTC datetime."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(
        start=start.isoformat(),
        end=end.isoformat() if end else None,
        interval="1d",
        auto_adjust=False,
    )
    if df.empty:
        log.warning("yfinance returned no rows for %s", symbol)
        return df
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    df = df[["open", "high", "low", "close", "volume"]].copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return validate_bars(df, symbol=symbol)


def ensure_ticker(session: Session, symbol: str) -> None:
    existing = session.execute(select(Ticker).where(Ticker.symbol == symbol)).scalar_one_or_none()
    if existing is None:
        session.add(Ticker(symbol=symbol, active=True))
        session.flush()


def upsert_bars(session: Session, symbol: str, df: pd.DataFrame) -> int:
    """Insert bars idempotently. Returns count of newly-inserted rows."""
    if df.empty:
        return 0
    clean_df = validate_bars(df, symbol=symbol)
    if clean_df.empty:
        return 0
    ensure_ticker(session, symbol)
    rows = [
        {
            "symbol": symbol,
            "ts": ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
            "source": "yfinance",
        }
        for ts, row in clean_df.iterrows()
    ]
    return upsert_ignore(session, PriceBar.__table__, rows, ["symbol", "ts"])


def ingest_symbol(session: Session, symbol: str, since: dt.date) -> int:
    df = fetch_ohlcv(symbol, since)
    inserted = upsert_bars(session, symbol, df)
    log.info("Ingested %d new bars for %s (since %s)", inserted, symbol, since)
    return inserted
