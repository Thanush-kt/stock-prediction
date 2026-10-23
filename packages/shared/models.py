"""ORM models for the Phase 1 data layer."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Ticker(Base):
    __tablename__ = "tickers"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    bars: Mapped[list["PriceBar"]] = relationship(back_populates="ticker")
    indicators: Mapped[list["Indicator"]] = relationship(back_populates="ticker")


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("tickers.symbol"), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="yfinance", nullable=False)

    ticker: Mapped[Ticker] = relationship(back_populates="bars")

    __table_args__ = (
        UniqueConstraint("symbol", "ts", name="uq_price_bars_symbol_ts"),
        Index("ix_price_bars_symbol_ts_desc", "symbol", "ts"),
    )


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("tickers.symbol"), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    ticker: Mapped[Ticker] = relationship(back_populates="indicators")

    __table_args__ = (
        UniqueConstraint("symbol", "ts", "name", name="uq_indicators_symbol_ts_name"),
        Index("ix_indicators_symbol_ts_desc", "symbol", "ts"),
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str | None] = mapped_column(
        String(16), ForeignKey("tickers.symbol"), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sentiment: Mapped["Sentiment | None"] = relationship(back_populates="news_item", uselist=False)

    __table_args__ = (
        Index("ix_news_items_symbol_published", "symbol", "published_at"),
    )


class Sentiment(Base):
    __tablename__ = "sentiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_items.id"), nullable=False, unique=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    compound: Mapped[float] = mapped_column(Float, nullable=False)
    pos: Mapped[float] = mapped_column(Float, nullable=False)
    neu: Mapped[float] = mapped_column(Float, nullable=False)
    neg: Mapped[float] = mapped_column(Float, nullable=False)

    news_item: Mapped[NewsItem] = relationship(back_populates="sentiment")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("tickers.symbol"), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    label_pred: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Phase 4 additions (migration 0005) -----------------------------------
    # target_session: the trading session this prediction applies to.
    # It is the next trading day after ts (data cutoff bar timestamp).
    target_session: Mapped[dt.date | None] = mapped_column(
        Date, nullable=True,
        comment="Next trading session after the data-cutoff bar (set by train/predict)"
    )
    # Explicit semantic alias for ts so callers are unambiguous.
    data_cutoff_ts: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Alias of ts — the last bar timestamp used as model input"
    )
    # Wall-clock timestamp when this row was written to the DB.
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        comment="Wall-clock time when this prediction row was written"
    )
    # Outcome tracking — filled by the evaluate-outcomes job.
    actual_close: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Actual closing price on target_session (set by evaluate-outcomes)"
    )
    actual_label: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="1 if actual_close > data-cutoff close, else 0 (set by evaluate-outcomes)"
    )
    evaluated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When actual_label was set by the evaluate-outcomes job"
    )
    # -------------------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "symbol", "ts", "model_version", name="uq_predictions_symbol_ts_model"
        ),
        Index("ix_predictions_symbol_ts", "symbol", "ts"),
        Index("ix_predictions_model_version", "model_version"),
        Index("ix_predictions_target_session", "target_session"),
        Index("ix_predictions_evaluated_at", "evaluated_at"),
    )


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    hit_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)
    n_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    __table_args__ = (Index("ix_backtest_runs_model_version", "model_version"),)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("tickers.symbol"), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    rationale: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "ts", "model_version", name="uq_signals_symbol_ts_model"
        ),
        Index("ix_signals_symbol_ts", "symbol", "ts"),
        Index("ix_signals_model_version", "model_version"),
        Index("ix_signals_decision", "decision"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("tickers.symbol"), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="market")
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    submitted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    filled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    signal_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("signals.id"), nullable=True
    )

    trades: Mapped[list["Trade"]] = relationship(back_populates="order")

    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_symbol_submitted_at", "symbol", "submitted_at"),
        Index(
            "uq_orders_signal_id",
            "signal_id",
            unique=True,
            postgresql_where=text("signal_id IS NOT NULL"),
            sqlite_where=text("signal_id IS NOT NULL"),
        ),
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    broker_trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    order: Mapped[Order] = relationship(back_populates="trades")

    __table_args__ = (Index("ix_trades_order_id", "order_id"),)


class Position(Base):
    __tablename__ = "positions"

    symbol: Mapped[str] = mapped_column(
        String(16), ForeignKey("tickers.symbol"), primary_key=True
    )
    qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="alpaca")


class RiskState(Base):
    __tablename__ = "risk_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    exposure_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    n_open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    halted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_risk_state_ts", "ts"),)
