"""Live market quote fetcher with an in-memory LRU cache.

Used by the FastAPI /stocks/{symbol}/market-data endpoint to serve
the current price without hammering yfinance on every request.

Cache policy:
  - Max 256 entries (LRU eviction).
  - Each entry expires after TTL_SECONDS (300 s = 5 min).
  - On any yfinance error the most recent cached value is returned
    if it exists, otherwise SymbolNotFoundError is raised.

The module is intentionally free of SQLAlchemy imports so it can be
used from both the API layer and the CLI without circular imports.
"""
from __future__ import annotations

import datetime as dt
import time
from functools import lru_cache
from typing import TypedDict

from packages.shared.logging import get_logger

log = get_logger(__name__)

TTL_SECONDS = 300  # 5 minutes
_cache: dict[str, tuple[float, dict]] = {}  # symbol -> (expires_at, data)
_MAX_ENTRIES = 256


class SymbolNotFoundError(ValueError):
    """Raised when yfinance cannot find the requested symbol."""


class QuoteData(TypedDict):
    symbol: str
    price: float
    currency: str
    ts: str
    open: float | None
    high: float | None
    low: float | None
    close_prev: float | None
    change_pct: float | None
    source: str


def _evict_oldest() -> None:
    """Drop the oldest entry when cache is full."""
    if len(_cache) >= _MAX_ENTRIES:
        oldest = min(_cache.items(), key=lambda kv: kv[1][0])
        del _cache[oldest[0]]


def get_latest_quote(symbol: str) -> QuoteData:
    """Return a live (or recently cached) quote for *symbol*.

    Falls back to the cached value if yfinance raises; raises
    SymbolNotFoundError if no data is available at all.
    """
    import yfinance as yf  # lazy import so tests can patch it

    now = time.monotonic()
    cached = _cache.get(symbol)
    if cached is not None and cached[0] > now:
        return cached[1]  # type: ignore[return-value]

    try:
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        price = getattr(fast, "last_price", None)
        if price is None or price != price:  # None or NaN
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found or has no price data")

        prev_close = getattr(fast, "previous_close", None)
        change_pct: float | None = None
        if prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 4)

        data: QuoteData = {
            "symbol": symbol,
            "price": float(price),
            "currency": getattr(fast, "currency", "USD") or "USD",
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "open": _safe_float(getattr(fast, "open", None)),
            "high": _safe_float(getattr(fast, "day_high", None)),
            "low": _safe_float(getattr(fast, "day_low", None)),
            "close_prev": _safe_float(prev_close),
            "change_pct": change_pct,
            "source": "live",
        }
        _evict_oldest()
        _cache[symbol] = (now + TTL_SECONDS, data)
        return data
    except SymbolNotFoundError:
        raise
    except Exception as exc:
        log.warning("yfinance error for %s: %s — returning cached value if available", symbol, exc)
        if cached is not None:
            stale = dict(cached[1])
            stale["source"] = "cached"
            return stale  # type: ignore[return-value]
        raise SymbolNotFoundError(f"Symbol '{symbol}' not found: {exc}") from exc


def _safe_float(value: object) -> float | None:
    try:
        v = float(value)  # type: ignore[arg-type]
        return v if v == v else None  # filter NaN
    except (TypeError, ValueError):
        return None


def validate_ticker(symbol: str) -> None:
    """Raise SymbolNotFoundError if *symbol* is not a valid yfinance ticker.

    Used by the ingestion pipeline to skip invalid symbols early.
    """
    import yfinance as yf  # lazy import

    ticker = yf.Ticker(symbol)
    fast = ticker.fast_info
    price = getattr(fast, "last_price", None)
    if price is None or price != price:
        raise SymbolNotFoundError(f"Symbol '{symbol}' is not valid or has no price data")
