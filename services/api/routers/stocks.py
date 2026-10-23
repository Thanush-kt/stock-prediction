"""GET /stocks — symbols, live quotes, price history, and risk analysis."""
from __future__ import annotations

import datetime as dt

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.shared.models import Indicator, PriceBar, Ticker
from services.api.deps import get_session
from services.api.schemas import (
    MarketDataOut,
    PriceBarOut,
    RiskAnalysisOut,
    TickerOut,
)
from services.ingestion.market_data import SymbolNotFoundError, get_latest_quote
from services.signal.validation import exchange_for_symbol

router = APIRouter()


def _enrich_ticker(t: Ticker) -> TickerOut:
    sym = t.symbol.upper()
    exch = exchange_for_symbol(sym)
    if exch == "CRYPTO":
        asset_class = "crypto"
    elif exch == "COMMODITY":
        asset_class = "commodity"
    else:
        asset_class = "equity"
    return TickerOut(
        symbol=t.symbol,
        name=t.name,
        exchange=exch,
        asset_class=asset_class,
        active=t.active,
    )


@router.get("/stocks", response_model=list[TickerOut])
def list_stocks(
    active_only: bool = True,
    session: Session = Depends(get_session),
) -> list[TickerOut]:
    """List all supported symbols from the tickers table."""
    stmt = select(Ticker).order_by(Ticker.symbol.asc())
    if active_only:
        stmt = stmt.where(Ticker.active == True)  # noqa: E712
    tickers = session.execute(stmt).scalars().all()
    return [_enrich_ticker(t) for t in tickers]


@router.get("/stocks/{symbol}/market-data", response_model=MarketDataOut)
def get_market_data(
    symbol: str,
    session: Session = Depends(get_session),
) -> MarketDataOut:
    """Return live or cached market quote, falling back to recent DB price bars."""
    sym = symbol.upper()

    # 1. Try live/cached quote from market_data service
    try:
        quote = get_latest_quote(sym)
        return MarketDataOut(
            symbol=sym,
            price=float(quote["price"]),
            currency=quote["currency"],
            ts=quote["ts"],
            open=quote.get("open"),
            high=quote.get("high"),
            low=quote.get("low"),
            close_prev=quote.get("close_prev"),
            change_pct=quote.get("change_pct"),
            source=quote.get("source", "live"),
        )
    except (SymbolNotFoundError, Exception):
        pass

    # 2. Fall back to latest price bar in DB
    last_bar = (
        session.execute(
            select(PriceBar)
            .where(PriceBar.symbol == sym)
            .order_by(PriceBar.ts.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    if last_bar is not None:
        currency = "INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD"
        return MarketDataOut(
            symbol=sym,
            price=float(last_bar.close),
            currency=currency,
            ts=last_bar.ts.isoformat(),
            open=float(last_bar.open) if last_bar.open is not None else None,
            high=float(last_bar.high) if last_bar.high is not None else None,
            low=float(last_bar.low) if last_bar.low is not None else None,
            close_prev=None,
            change_pct=None,
            source="db",
        )

    raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")


@router.get("/stocks/{symbol}/price-history", response_model=list[PriceBarOut])
def get_price_history(
    symbol: str,
    days: int = Query(90, ge=5, le=3650),
    session: Session = Depends(get_session),
) -> list[PriceBarOut]:
    """Return historical daily OHLCV bars for charts."""
    sym = symbol.upper()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    rows = (
        session.execute(
            select(PriceBar)
            .where(PriceBar.symbol == sym, PriceBar.ts >= cutoff)
            .order_by(PriceBar.ts.asc())
        )
        .scalars()
        .all()
    )
    return [PriceBarOut.model_validate(r) for r in rows]


@router.get("/stocks/{symbol}/risk", response_model=RiskAnalysisOut)
def get_risk_analysis(
    symbol: str,
    session: Session = Depends(get_session),
) -> RiskAnalysisOut:
    """Return risk metrics (volatility, ATR, drawdown, stop-loss, suggested sizing)."""
    sym = symbol.upper()
    now_utc = dt.datetime.now(dt.timezone.utc)

    bars = (
        session.execute(
            select(PriceBar)
            .where(PriceBar.symbol == sym)
            .order_by(PriceBar.ts.desc())
            .limit(252)
        )
        .scalars()
        .all()
    )
    bars = list(reversed(bars))

    closes = [float(b.close) for b in bars if b.close is not None and b.close > 0]
    hist_vol_20: float | None = None
    hist_vol_60: float | None = None
    max_dd: float | None = None

    if len(closes) >= 2:
        returns = np.diff(np.log(closes))
        if len(returns) >= 20:
            hist_vol_20 = round(float(np.std(returns[-20:]) * np.sqrt(252)), 4)
        if len(returns) >= 60:
            hist_vol_60 = round(float(np.std(returns[-60:]) * np.sqrt(252)), 4)

        cum_max = np.maximum.accumulate(closes)
        drawdowns = (cum_max - closes) / cum_max
        max_dd = round(float(np.max(drawdowns)), 4)

    # Fetch latest ATR from indicators table if computed
    latest_atr = (
        session.execute(
            select(Indicator.value)
            .where(Indicator.symbol == sym, Indicator.name == "atr_14")
            .order_by(Indicator.ts.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    atr_val = round(float(latest_atr), 4) if latest_atr is not None else None

    # Determine risk category & suggested position percentage
    ref_vol = hist_vol_20 if hist_vol_20 is not None else 0.25
    if ref_vol > 0.50:
        risk_cat = "VERY HIGH"
        suggested_pct = 0.04
        explanation = f"High annualized volatility ({ref_vol:.1%}); conservative position sizing recommended."
    elif ref_vol > 0.35:
        risk_cat = "HIGH"
        suggested_pct = 0.06
        explanation = f"Elevated volatility ({ref_vol:.1%}); reduce exposure to manage downside tail risk."
    elif ref_vol > 0.20:
        risk_cat = "MEDIUM"
        suggested_pct = 0.10
        explanation = f"Moderate volatility ({ref_vol:.1%}); standard position sizing parameters apply."
    else:
        risk_cat = "LOW"
        suggested_pct = 0.15
        explanation = f"Low annualized volatility ({ref_vol:.1%}); stable asset suitable for standard allocation."

    return RiskAnalysisOut(
        symbol=sym,
        hist_volatility_20d=hist_vol_20,
        hist_volatility_60d=hist_vol_60,
        atr_14=atr_val,
        max_drawdown_1y=max_dd,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        risk_reward_ratio=2.0,
        suggested_position_pct=suggested_pct,
        risk_category=risk_cat,
        risk_explanation=explanation,
        as_of=now_utc,
    )
