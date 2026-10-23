"""GET /predictions — recent model predictions, latest per symbol, and accuracy metrics."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from packages.shared.models import Prediction, Ticker
from services.api.deps import get_session
from services.api.schemas import (
    MarketDataOut,
    PredictionAccuracyOut,
    PredictionOut,
    SessionPredictionDetail,
    StockPredictionSessionsOut,
)
from services.ingestion.market_data import SymbolNotFoundError, get_latest_quote
from services.signal.validation import (
    exchange_for_symbol,
    exchange_timezone,
    get_current_trading_session,
    get_exchange_local_date,
    get_next_trading_session_date,
    is_market_session_open,
    is_trading_day,
    trading_days_between,
)

router = APIRouter()


@router.get("/predictions/sessions", response_model=list[StockPredictionSessionsOut])
def get_prediction_sessions(
    symbol: str | None = None,
    model_version: str | None = None,
    session: Session = Depends(get_session),
) -> list[StockPredictionSessionsOut]:
    """Return structured predictions for today's session and the next trading session."""
    if symbol is not None:
        target_symbols = [symbol.upper()]
    else:
        tickers = session.execute(
            select(Ticker.symbol).where(Ticker.active == True).order_by(Ticker.symbol)  # noqa: E712
        ).scalars().all()
        target_symbols = list(tickers) if tickers else ["AAPL", "MSFT", "NVDA"]

    results: list[StockPredictionSessionsOut] = []
    now_utc = dt.datetime.now(dt.timezone.utc)

    for sym in target_symbols:
        exch = exchange_for_symbol(sym)
        tz = exchange_timezone(exch)
        now_local = now_utc.astimezone(tz)
        today_session = get_current_trading_session(exchange=exch, as_of=now_utc)
        next_session = get_next_trading_session_date(today_session, exchange=exch)
        is_open = is_market_session_open(exchange=exch, as_of=now_utc)

        # 1. Latest Market Data quote
        quote_out: MarketDataOut | None = None
        try:
            q = get_latest_quote(sym)
            quote_out = MarketDataOut(
                symbol=sym,
                price=float(q["price"]),
                currency=q["currency"],
                ts=q["ts"],
                open=q.get("open"),
                high=q.get("high"),
                low=q.get("low"),
                close_prev=q.get("close_prev"),
                change_pct=q.get("change_pct"),
                source=q.get("source", "live"),
            )
        except Exception:
            pass

        # 2. Today's prediction
        q_today = select(Prediction).where(
            Prediction.symbol == sym,
            Prediction.target_session == today_session,
        )
        if model_version:
            q_today = q_today.where(Prediction.model_version == model_version)
        pred_today = session.execute(
            q_today.order_by(Prediction.ts.desc(), Prediction.id.desc()).limit(1)
        ).scalar_one_or_none()

        today_detail: SessionPredictionDetail
        if pred_today:
            timing = "before_session"
            if pred_today.generated_at:
                gen_local = pred_today.generated_at.astimezone(tz).time()
                if exch == "NYSE":
                    timing = (
                        "before_session"
                        if gen_local < dt.time(9, 30)
                        else ("during_session" if gen_local <= dt.time(16, 0) else "after_session")
                    )
                elif exch == "NSE":
                    timing = (
                        "before_session"
                        if gen_local < dt.time(9, 15)
                        else ("during_session" if gen_local <= dt.time(15, 30) else "after_session")
                    )
                else:
                    timing = "during_session"

            actual_outcome: str | None = None
            if pred_today.actual_label is not None:
                actual_outcome = (
                    "correct" if pred_today.actual_label == pred_today.label_pred else "incorrect"
                )
            else:
                actual_outcome = "pending"

            cutoff_date = get_exchange_local_date(
                pred_today.data_cutoff_ts or pred_today.ts, exchange=exch
            )
            lag_days = trading_days_between(cutoff_date, today_session, exchange=exch)
            status = "stale" if lag_days > 1 else "available"

            today_detail = SessionPredictionDetail(
                target_session=today_session,
                session_label="Today's Session",
                is_trading_day=is_trading_day(today_session, exchange=exch),
                status=status,
                timing=timing,
                prediction=PredictionOut.model_validate(pred_today),
                actual_outcome=actual_outcome,
                message=None if status == "available" else f"Prediction based on older data ({cutoff_date}).",
            )
        else:
            today_detail = SessionPredictionDetail(
                target_session=today_session,
                session_label="Today's Session",
                is_trading_day=is_trading_day(today_session, exchange=exch),
                status="unavailable",
                timing=None,
                prediction=None,
                actual_outcome=None,
                message=f"No prediction available for today's trading session ({today_session}).",
            )

        # 3. Tomorrow's (Next Session) prediction
        q_tomorrow = select(Prediction).where(
            Prediction.symbol == sym,
            Prediction.target_session == next_session,
        )
        if model_version:
            q_tomorrow = q_tomorrow.where(Prediction.model_version == model_version)
        pred_tomorrow = session.execute(
            q_tomorrow.order_by(Prediction.ts.desc(), Prediction.id.desc()).limit(1)
        ).scalar_one_or_none()

        tomorrow_detail: SessionPredictionDetail
        if pred_tomorrow:
            tomorrow_detail = SessionPredictionDetail(
                target_session=next_session,
                session_label="Next Trading Session",
                is_trading_day=True,
                status="available",
                timing="future_session",
                prediction=PredictionOut.model_validate(pred_tomorrow),
                actual_outcome="pending",
                message=None,
            )
        else:
            close_time = (
                dt.time(16, 0)
                if exch == "NYSE"
                else (dt.time(15, 30) if exch == "NSE" else dt.time(23, 59))
            )
            if now_local.date() == today_session and (is_open or now_local.time() < close_time):
                status = "pending_close"
                msg = f"Prediction for session {next_session} will generate after today's market session ({today_session}) completes."
            else:
                status = "unavailable"
                msg = f"Awaiting market data ingestion for session {next_session}."

            tomorrow_detail = SessionPredictionDetail(
                target_session=next_session,
                session_label="Next Trading Session",
                is_trading_day=True,
                status=status,
                timing=None,
                prediction=None,
                actual_outcome=None,
                message=msg,
            )

        results.append(
            StockPredictionSessionsOut(
                symbol=sym,
                exchange=exch,
                exchange_timezone=str(tz),
                is_market_open=is_open,
                current_session_date=today_session,
                next_session_date=next_session,
                today=today_detail,
                tomorrow=tomorrow_detail,
                latest_quote=quote_out,
            )
        )

    return results


@router.get("/predictions/latest", response_model=list[PredictionOut])
def latest_predictions(
    symbol: str | None = None,
    model_version: str | None = None,
    session: Session = Depends(get_session),
) -> list[PredictionOut]:
    """Return the single most recent prediction for each (symbol, model_version) pair."""
    subq = (
        select(
            Prediction.symbol,
            Prediction.model_version,
            func.max(Prediction.ts).label("max_ts"),
        )
        .group_by(Prediction.symbol, Prediction.model_version)
    )
    if symbol is not None:
        subq = subq.where(Prediction.symbol == symbol.upper())
    if model_version is not None:
        subq = subq.where(Prediction.model_version == model_version)
    subq = subq.subquery()

    stmt = (
        select(Prediction)
        .join(
            subq,
            (Prediction.symbol == subq.c.symbol)
            & (Prediction.model_version == subq.c.model_version)
            & (Prediction.ts == subq.c.max_ts),
        )
        .order_by(Prediction.symbol)
    )
    rows = session.execute(stmt).scalars().all()
    return [PredictionOut.model_validate(r) for r in rows]


@router.get("/predictions/accuracy", response_model=list[PredictionAccuracyOut])
def prediction_accuracy(
    symbol: str | None = None,
    model_version: str | None = None,
    days: int = Query(90, ge=7, le=365),
    session: Session = Depends(get_session),
) -> list[PredictionAccuracyOut]:
    """Return accuracy metrics for evaluated predictions over the past N days."""
    cutoff_date = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=days)

    stmt = (
        select(
            Prediction.symbol,
            Prediction.model_version,
            func.count(Prediction.id).label("n_evaluated"),
            func.sum(
                case((Prediction.actual_label == Prediction.label_pred, 1), else_=0)
            ).label("n_correct"),
        )
        .where(
            Prediction.actual_label.is_not(None),
            Prediction.target_session.is_not(None),
            Prediction.target_session >= cutoff_date,
        )
        .group_by(Prediction.symbol, Prediction.model_version)
        .order_by(Prediction.symbol)
    )

    if symbol is not None:
        stmt = stmt.where(Prediction.symbol == symbol.upper())
    if model_version is not None:
        stmt = stmt.where(Prediction.model_version == model_version)

    rows = session.execute(stmt).all()
    results: list[PredictionAccuracyOut] = []
    for r in rows:
        n_eval = int(r.n_evaluated or 0)
        n_corr = int(r.n_correct or 0)
        acc = round(n_corr / n_eval, 4) if n_eval > 0 else 0.0
        results.append(
            PredictionAccuracyOut(
                symbol=r.symbol,
                model_version=r.model_version,
                n_evaluated=n_eval,
                n_correct=n_corr,
                accuracy=acc,
                period_days=days,
            )
        )
    return results


@router.get("/predictions", response_model=list[PredictionOut])
def list_predictions(
    limit: int = Query(50, ge=1, le=500),
    symbol: str | None = None,
    model_version: str | None = None,
    target_session_from: dt.date | None = None,
    target_session_to: dt.date | None = None,
    session: Session = Depends(get_session),
) -> list[PredictionOut]:
    stmt = select(Prediction).order_by(Prediction.ts.desc(), Prediction.id.desc()).limit(limit)
    if symbol is not None:
        stmt = stmt.where(Prediction.symbol == symbol.upper())
    if model_version is not None:
        stmt = stmt.where(Prediction.model_version == model_version)
    if target_session_from is not None:
        stmt = stmt.where(Prediction.target_session >= target_session_from)
    if target_session_to is not None:
        stmt = stmt.where(Prediction.target_session <= target_session_to)
    rows = session.execute(stmt).scalars().all()
    return [PredictionOut.model_validate(r) for r in rows]

