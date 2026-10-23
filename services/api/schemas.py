"""Pydantic response models for the dashboard API."""
from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict


class _ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PositionOut(_ApiModel):
    symbol: str
    qty: float
    avg_price: float
    updated_at: dt.datetime
    source: str


class SignalOut(_ApiModel):
    id: int
    symbol: str
    ts: dt.datetime
    model_version: str
    score: float
    decision: str
    rationale: dict[str, Any]
    created_at: dt.datetime


class OrderOut(_ApiModel):
    id: int
    symbol: str
    side: str
    qty: float
    order_type: str
    limit_price: float | None
    stop_price: float | None
    take_profit: float | None
    status: str
    submitted_at: dt.datetime
    filled_at: dt.datetime | None
    broker_order_id: str | None
    signal_id: int | None


class EquityPoint(_ApiModel):
    ts: dt.datetime
    equity: float
    cash: float
    exposure_pct: float
    max_drawdown: float
    n_open_positions: int
    halted: bool


class PredictionOut(_ApiModel):
    id: int
    symbol: str
    ts: dt.datetime
    model_version: str
    score: float
    label_pred: int
    target_session: dt.date | None = None
    data_cutoff_ts: dt.datetime | None = None
    generated_at: dt.datetime | None = None
    actual_close: float | None = None
    actual_label: int | None = None
    evaluated_at: dt.datetime | None = None


class SessionPredictionDetail(BaseModel):
    target_session: dt.date
    session_label: str
    is_trading_day: bool
    status: str  # available | pending_close | stale | unavailable
    timing: str | None = None  # before_session | during_session | future_session
    prediction: PredictionOut | None = None
    actual_outcome: str | None = None  # correct | incorrect | pending
    message: str | None = None


class StockPredictionSessionsOut(BaseModel):
    symbol: str
    exchange: str
    exchange_timezone: str
    is_market_open: bool
    current_session_date: dt.date
    next_session_date: dt.date
    today: SessionPredictionDetail
    tomorrow: SessionPredictionDetail
    latest_quote: MarketDataOut | None = None


class PredictionAccuracyOut(BaseModel):
    symbol: str
    model_version: str
    n_evaluated: int
    n_correct: int
    accuracy: float
    period_days: int


class TickerOut(_ApiModel):
    symbol: str
    name: str | None = None
    exchange: str
    asset_class: str
    active: bool


class MarketDataOut(BaseModel):
    symbol: str
    price: float
    currency: str
    ts: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close_prev: float | None = None
    change_pct: float | None = None
    source: str


class PriceBarOut(_ApiModel):
    symbol: str
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class RiskAnalysisOut(BaseModel):
    symbol: str
    hist_volatility_20d: float | None = None
    hist_volatility_60d: float | None = None
    atr_14: float | None = None
    max_drawdown_1y: float | None = None
    stop_loss_pct: float
    take_profit_pct: float
    risk_reward_ratio: float
    suggested_position_pct: float
    risk_category: str
    risk_explanation: str
    as_of: dt.datetime


class HealthOut(BaseModel):
    status: str = "ok"
