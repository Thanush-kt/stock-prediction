"""Signal runner: load latest predictions+features+positions → decide → write signals+orders."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.shared.config import get_settings
from packages.shared.db import run_signals_lock, upsert_ignore
from packages.shared.logging import get_logger
from packages.shared.models import Order, Position, Prediction, PriceBar, RiskState, Signal
from services.broker.alpaca import AlpacaClient, AlpacaError
from services.model.features import build_feature_matrix
from services.signal.rules import (
    DEFAULT_MAX_EXPOSURE_PCT,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_SENTIMENT_FLOOR,
    DEFAULT_TARGET_PCT,
    DEFAULT_THRESHOLD,
    SignalDecision,
    decide,
)
from services.signal.validation import validate_prediction

log = get_logger(__name__)

STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04


@dataclass
class RunSummary:
    halted: bool = False
    n_signals: int = 0
    n_buy: int = 0
    n_sell: int = 0
    n_hold: int = 0
    n_orders_submitted: int = 0
    n_orders_dry_run: int = 0
    errors: list[str] = field(default_factory=list)


def _latest_predictions(session: Session, model_version: str) -> pd.DataFrame:
    if not model_version or not str(model_version).strip():
        return pd.DataFrame(columns=["symbol", "ts", "score", "model_version"])
    rows = session.execute(
        select(Prediction.symbol, Prediction.ts, Prediction.score, Prediction.model_version)
        .where(Prediction.model_version == model_version)
        .order_by(Prediction.symbol, Prediction.ts.desc())
    ).all()
    if not rows:
        return pd.DataFrame(columns=["symbol", "ts", "score", "model_version"])
    df = pd.DataFrame(rows, columns=["symbol", "ts", "score", "model_version"])
    return df.groupby("symbol", as_index=False).first()


def _latest_features(session: Session) -> pd.DataFrame:
    df = build_feature_matrix(session, require_target=False)
    if df.empty:
        return df
    latest = df.sort_values("ts").groupby("symbol", as_index=False).tail(1)
    closes = pd.DataFrame(
        session.execute(select(PriceBar.symbol, PriceBar.ts, PriceBar.close)).all(),
        columns=["symbol", "ts", "close"],
    )
    if closes.empty:
        latest = latest.copy()
        latest["close"] = float("nan")
        return latest
    closes["ts"] = pd.to_datetime(closes["ts"], utc=True).dt.tz_localize(None)
    latest = latest.copy()
    latest["ts"] = pd.to_datetime(latest["ts"], utc=True).dt.tz_localize(None)
    return latest.merge(closes, on=["symbol", "ts"], how="left")


TERMINAL_ORDER_STATUSES = {
    "filled",
    "canceled",
    "cancelled",
    "rejected",
    "expired",
    "dry_run",
}


def _portfolio_state(  # pylint: disable=too-many-locals
    session: Session,
    latest_prices: dict[str, float] | None = None,
) -> tuple[float, float, int, dict[str, float], dict[str, float]]:
    """Returns (equity, total_exposure_pct, n_open_positions,
    effective_qty_by_symbol, available_sell_by_symbol)."""
    rs = session.execute(
        select(RiskState).order_by(RiskState.ts.desc()).limit(1)
    ).scalar_one_or_none()
    equity = float(rs.equity) if rs is not None else 0.0
    exposure_pct = float(rs.exposure_pct) if rs is not None else 0.0

    pos_rows = session.execute(
        select(Position.symbol, Position.qty).where(Position.qty != 0)
    ).all()
    held_qty_by_symbol = {str(sym): float(qty) for sym, qty in pos_rows}

    # Query in-flight orders (non-terminal)
    open_orders = session.execute(
        select(Order).where(Order.status.notin_(list(TERMINAL_ORDER_STATUSES)))
    ).scalars().all()

    in_flight_buy_qty: dict[str, float] = {}
    in_flight_sell_qty: dict[str, float] = {}
    in_flight_buy_notional = 0.0

    for o in open_orders:
        sym = str(o.symbol)
        filled_qty = sum(float(t.qty) for t in o.trades)
        unfilled_qty = max(float(o.qty) - filled_qty, 0.0)
        if unfilled_qty <= 0:
            continue

        if o.side == "buy":
            in_flight_buy_qty[sym] = in_flight_buy_qty.get(sym, 0.0) + unfilled_qty
            price = latest_prices.get(sym) if latest_prices else None
            if price is None or price <= 0:
                bar_close = session.execute(
                    select(PriceBar.close).where(PriceBar.symbol == sym).order_by(PriceBar.ts.desc()).limit(1)
                ).scalar_one_or_none()
                price = float(bar_close) if bar_close is not None else 0.0
            if price > 0:
                in_flight_buy_notional += unfilled_qty * price
            elif equity > 0:
                in_flight_buy_notional += equity * (DEFAULT_TARGET_PCT / 100.0)
        elif o.side == "sell":
            in_flight_sell_qty[sym] = in_flight_sell_qty.get(sym, 0.0) + unfilled_qty

    in_flight_exposure_pct = (in_flight_buy_notional / equity * 100.0) if equity > 0 else 0.0
    total_exposure_pct = exposure_pct + in_flight_exposure_pct

    # Active symbols = settled long positions + in-flight buy orders
    active_symbols = {
        sym for sym, qty in held_qty_by_symbol.items() if qty > 0
    } | {
        sym for sym, qty in in_flight_buy_qty.items() if qty > 0
    }
    n_open = len(active_symbols)

    all_symbols = set(held_qty_by_symbol.keys()) | set(in_flight_buy_qty.keys())
    effective_qty_by_symbol: dict[str, float] = {}
    for sym in all_symbols:
        h = held_qty_by_symbol.get(sym, 0.0)
        b = in_flight_buy_qty.get(sym, 0.0)
        s = in_flight_sell_qty.get(sym, 0.0)
        effective_qty_by_symbol[sym] = max(h + b - s, 0.0)

    available_sell_by_symbol: dict[str, float] = {}
    for sym, h in held_qty_by_symbol.items():
        if h > 0:
            s = in_flight_sell_qty.get(sym, 0.0)
            available_sell_by_symbol[sym] = max(h - s, 0.0)

    return equity, total_exposure_pct, n_open, effective_qty_by_symbol, available_sell_by_symbol


def _qty_for_target(target_pct: float, equity: float, price: float) -> int:
    if equity <= 0 or price <= 0:
        return 0
    notional = equity * (target_pct / 100.0)
    return max(int(notional // price), 0)


def _persist_signal(
    session: Session,
    model_version: str,
    ts: dt.datetime,
    score: float,
    decision: SignalDecision,
) -> Signal | None:
    inserted = upsert_ignore(
        session,
        Signal.__table__,
        [
            {
                "symbol": decision.symbol,
                "ts": ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                "model_version": model_version,
                "score": float(score),
                "decision": decision.decision,
                "rationale": decision.rationale,
            }
        ],
        ["symbol", "ts", "model_version"],
    )
    if inserted == 0:
        return None
    return session.execute(
        select(Signal)
        .where(Signal.symbol == decision.symbol)
        .where(Signal.ts == ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts)
        .where(Signal.model_version == model_version)
    ).scalar_one_or_none()


def _submit_order(  # pylint: disable=too-many-branches,too-many-statements,too-many-return-statements,broad-exception-caught
    session: Session,
    signal_row: Signal,
    decision: SignalDecision,
    close: float,
    equity: float,
    alpaca: AlpacaClient | None,
    summary: RunSummary,
    current_position_qty: float = 0.0,
) -> float:
    # Prevent duplicate order if one already exists for this signal
    existing_order = session.execute(
        select(Order).where(Order.signal_id == signal_row.id)
    ).scalar_one_or_none()
    if existing_order is not None:
        log.warning(
            "Order already exists for signal %d (status=%s), skipping",
            signal_row.id,
            existing_order.status,
        )
        return 0.0

    side = "buy" if decision.decision == "BUY" else "sell"

    if side == "buy":
        qty = _qty_for_target(decision.target_pct, equity, close)
        if qty <= 0:
            log.info(
                "buy %s: target qty <= 0 (equity=%.2f close=%.2f), skipping",
                decision.symbol, equity, close,
            )
            return 0.0
        take_profit = close * (1.0 + TAKE_PROFIT_PCT)
        stop_loss = close * (1.0 - STOP_LOSS_PCT)
    else:  # sell
        if current_position_qty <= 0:
            log.warning(
                "sell %s: current position qty is not positive (%.4f), skipping",
                decision.symbol, current_position_qty,
            )
            return 0.0
        qty = current_position_qty
        if qty <= 0:
            log.warning(
                "sell %s: invalid sell qty <= 0 (%.4f), skipping",
                decision.symbol, qty,
            )
            return 0.0
        qty = min(qty, current_position_qty)
        if isinstance(qty, float) and qty.is_integer():
            qty = int(qty)
        take_profit = None
        stop_loss = None

    order = Order(
        symbol=decision.symbol,
        side=side,
        qty=float(qty),
        order_type="market",
        take_profit=take_profit,
        stop_price=stop_loss,
        status="pending",
        signal_id=signal_row.id,
    )
    session.add(order)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        log.warning(
            "Order insertion blocked by unique constraint for signal %d: %s",
            signal_row.id,
            exc,
        )
        return 0.0

    if alpaca is None:
        order.status = "dry_run"
        summary.n_orders_dry_run += 1
        session.commit()
        log.info("DRY RUN order: %s %s qty=%s", side, decision.symbol, qty)
        return float(qty)

    client_order_id = f"sp-sig-{signal_row.id}"
    try:
        if side == "buy":
            resp = alpaca.submit_bracket_order(
                symbol=decision.symbol,
                qty=qty,
                side=side,
                take_profit=take_profit,  # type: ignore[arg-type]
                stop_loss=stop_loss,  # type: ignore[arg-type]
                client_order_id=client_order_id,
            )
        else:
            resp = alpaca.submit_market_order(
                symbol=decision.symbol,
                qty=qty,
                side=side,
                client_order_id=client_order_id,
            )
        order.broker_order_id = resp.get("id")
        order.status = resp.get("status", "submitted")
        summary.n_orders_submitted += 1
        session.commit()
        log.info(
            "Submitted %s %s qty=%s broker_id=%s",
            side, decision.symbol, qty, order.broker_order_id,
        )
        return float(qty)
    except AlpacaError as exc:
        if getattr(exc, "is_duplicate", False):
            broker_order: dict[str, Any] | None = None
            if hasattr(alpaca, "get_order_by_client_id"):
                try:
                    broker_order = alpaca.get_order_by_client_id(client_order_id)
                except Exception as fetch_exc:
                    log.warning(
                        "Could not fetch existing order by client_id %s: %s",
                        client_order_id,
                        fetch_exc,
                    )
            if broker_order and broker_order.get("id"):
                order.broker_order_id = broker_order.get("id")
                order.status = broker_order.get("status") or "unknown"
            else:
                order.status = "unknown"
            summary.errors.append(f"{decision.symbol} (duplicate_client_order_id): {exc}")
            log.warning(
                "Alpaca reported duplicate client_order_id for %s; recorded status=%s for reconciliation",
                decision.symbol,
                order.status,
            )
            try:
                session.commit()
            except Exception as commit_exc:
                log.exception("Failed to commit order status for %s: %s", decision.symbol, commit_exc)
                session.rollback()
            return float(qty)
        if getattr(exc, "is_ambiguous", False):
            order.status = "unknown"
            summary.errors.append(f"{decision.symbol} (ambiguous): {exc}")
            log.error("Alpaca submission outcome ambiguous for %s: %s", decision.symbol, exc)
            try:
                session.commit()
            except Exception as commit_exc:
                log.exception("Failed to commit order status for %s: %s", decision.symbol, commit_exc)
                session.rollback()
            return float(qty)
        order.status = "rejected"
        summary.errors.append(f"{decision.symbol}: {exc}")
        log.error("Alpaca submission rejected for %s: %s", decision.symbol, exc)
        try:
            session.commit()
        except Exception as commit_exc:
            log.exception("Failed to commit order status for %s: %s", decision.symbol, commit_exc)
            session.rollback()
        return 0.0
    except Exception as exc:
        order.status = "unknown"
        summary.errors.append(f"{decision.symbol}: {exc}")
        log.exception("Unexpected error submitting order for %s: %s", decision.symbol, exc)
        try:
            session.commit()
        except Exception as commit_exc:
            log.exception("Failed to commit order status for %s: %s", decision.symbol, commit_exc)
            session.rollback()
        return float(qty)


def _check_prediction_validity(  # pylint: disable=too-many-arguments
    session: Session,
    sym_str: str,
    row: Any,
    model_version: str,
    as_of: dt.datetime,
    max_age_days: int | None,
    max_trading_days: int | None,
) -> tuple[bool, str | None]:
    row_model_version = getattr(row, "model_version", model_version)
    is_valid, validation_error = validate_prediction(
        symbol=sym_str,
        ts=row.ts,
        pred_model_version=row_model_version,
        expected_model_version=model_version,
        as_of=as_of,
        max_age_days=max_age_days,
        max_trading_days=max_trading_days,
    )
    if not is_valid:
        return False, validation_error

    latest_bar_ts = session.execute(
        select(PriceBar.ts)
        .where(PriceBar.symbol == sym_str)
        .order_by(PriceBar.ts.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_bar_ts is not None:
        bar_ts_norm = pd.to_datetime(latest_bar_ts, utc=True).tz_localize(None)
        pred_ts_norm = pd.to_datetime(row.ts, utc=True).tz_localize(None)
        if bar_ts_norm > pred_ts_norm:
            return False, (
                f"{sym_str}: stale_prediction: prediction ts ({pred_ts_norm}) lags "
                f"behind latest price bar ({bar_ts_norm})"
            )

    return True, None


def run_once(  # pylint: disable=too-many-branches,too-many-locals,too-many-statements,too-many-return-statements
    session: Session,
    model_version: str,
    *,
    alpaca: AlpacaClient | None = None,
    as_of: dt.datetime | None = None,
    max_age_days: int | None = None,
    max_trading_days: int | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    sentiment_floor: float = DEFAULT_SENTIMENT_FLOOR,
    target_pct: float = DEFAULT_TARGET_PCT,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    max_exposure_pct: float = DEFAULT_MAX_EXPOSURE_PCT,
) -> RunSummary:
    summary = RunSummary()

    if not model_version or not str(model_version).strip():
        log.error("run_once: model_version is missing or empty")
        summary.errors.append("invalid_model_version: model_version cannot be empty")
        return summary

    if get_settings().risk_halt:
        log.warning("RISK_HALT is set — no signals will be processed")
        summary.halted = True
        return summary

    with run_signals_lock(session.get_bind()) as acquired:
        if not acquired:
            log.warning("run_once: another signal-runner process is currently running; skipping")
            summary.errors.append("run_signals_locked: another execution is in progress")
            return summary

        current_as_of = as_of or dt.datetime.now(dt.timezone.utc)

        preds = _latest_predictions(session, model_version)
        if preds.empty:
            log.warning("run_once: no predictions found for model_version=%s", model_version)
            return summary

        feats = _latest_features(session)
        if feats.empty:
            log.warning("run_once: no feature rows available")
            return summary

        # Normalize ts to tz-naive on both sides so merges work across dialects.
        preds = preds.copy()
        feats = feats.copy()
        preds["ts"] = pd.to_datetime(preds["ts"], utc=True).dt.tz_localize(None)
        feats["ts"] = pd.to_datetime(feats["ts"], utc=True).dt.tz_localize(None)

        merged = preds.merge(
            feats[["symbol", "ts", "close", "sma_50", "sent_mean_7d"]],
            on=["symbol", "ts"],
            how="inner",
        )
        if merged.empty:
            log.warning(
                "run_once: no (symbol, ts) match between predictions and features for %s",
                model_version,
            )
            return summary

        closes_map: dict[str, float] = {}
        if not feats.empty and "close" in feats.columns:
            for r in feats.itertuples(index=False):
                if pd.notna(r.close):
                    closes_map[str(r.symbol)] = float(r.close)

        equity, exposure_pct, _n_open, effective_qty_by_symbol, available_sell_by_symbol = (
            _portfolio_state(session, latest_prices=closes_map)
        )
        active_symbols = {
            sym for sym, qty in effective_qty_by_symbol.items() if qty > 0
        }

        for row in merged.itertuples(index=False):
            sym_str = str(row.symbol)
            is_valid, validation_error = _check_prediction_validity(
                session,
                sym_str,
                row,
                model_version,
                current_as_of,
                max_age_days,
                max_trading_days,
            )
            if not is_valid:
                log.warning("Validation failed for %s: %s", sym_str, validation_error)
                summary.errors.append(validation_error or f"{sym_str}: invalid prediction")
                continue

            current_pos_qty = effective_qty_by_symbol.get(sym_str, 0.0)
            decision = decide(
                symbol=sym_str,
                score=float(row.score),
                close=float(row.close),
                sma_50=float(row.sma_50),
                sentiment_7d=float(row.sent_mean_7d),
                current_position_qty=current_pos_qty,
                current_exposure_pct=exposure_pct,
                n_open_positions=len(active_symbols),
                threshold=threshold,
                sentiment_floor=sentiment_floor,
                target_pct=target_pct,
                max_positions=max_positions,
                max_exposure_pct=max_exposure_pct,
            )
            summary.n_signals += 1
            if decision.decision == "BUY":
                summary.n_buy += 1
            elif decision.decision == "SELL":
                summary.n_sell += 1
            else:
                summary.n_hold += 1

            sig = _persist_signal(session, model_version, row.ts, float(row.score), decision)
            session.commit()
            if sig is None:
                continue
            if decision.decision in ("BUY", "SELL"):
                submitted_qty = _submit_order(
                    session,
                    sig,
                    decision,
                    float(row.close),
                    equity,
                    alpaca,
                    summary,
                    current_position_qty=available_sell_by_symbol.get(sym_str, 0.0),
                )
                if decision.decision == "BUY" and submitted_qty > 0:
                    active_symbols.add(sym_str)
                    exposure_pct += decision.target_pct
                    effective_qty_by_symbol[sym_str] = current_pos_qty + submitted_qty
                elif decision.decision == "SELL" and submitted_qty > 0:
                    available_sell_by_symbol[sym_str] = max(
                        available_sell_by_symbol.get(sym_str, 0.0) - submitted_qty, 0.0
                    )
                    effective_qty_by_symbol[sym_str] = max(
                        current_pos_qty - submitted_qty, 0.0
                    )

    return summary
