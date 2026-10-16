"""Signal runner integration tests.

Stub the feature matrix to keep the test focused on signal/order writing
behaviour; the feature matrix itself is covered by tests/test_model_features.py.
"""
# pylint: disable=too-many-lines
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import select

from packages.shared.config import get_settings
from packages.shared.models import Order, Position, Prediction, RiskState, Signal, Ticker
from services.broker.alpaca import AlpacaError
from services.signal import runner as runner_mod


def _seed_prediction(
    session,
    symbol: str = "AAPL",
    score: float = 0.7,
    ts: dt.datetime | None = None,
    model_version: str = "v1",
):
    session.add(Ticker(symbol=symbol, active=True))
    session.flush()
    if ts is None:
        ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    session.add(
        Prediction(
            symbol=symbol,
            ts=ts,
            model_version=model_version,
            score=score,
            label_pred=int(score >= 0.5),
        )
    )
    session.flush()
    return symbol, ts


def _seed_risk_state(session, equity: float = 100_000.0):
    session.add(
        RiskState(
            ts=dt.datetime.now(dt.timezone.utc),
            equity=equity,
            cash=equity,
            exposure_pct=0.0,
            n_open_positions=0,
            halted=False,
        )
    )
    session.flush()


def _stub_features(monkeypatch, symbol: str, ts: dt.datetime, *, close: float, sma_50: float, sent: float):
    df = pd.DataFrame(
        [{"symbol": symbol, "ts": ts, "close": close, "sma_50": sma_50, "sent_mean_7d": sent}]
    )
    monkeypatch.setattr(runner_mod, "_latest_features", lambda _session: df)


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    from packages.shared import config as cfg
    monkeypatch.setattr(cfg, "_settings", None)
    monkeypatch.setenv("RISK_HALT", "0")
    yield
    monkeypatch.setattr(cfg, "_settings", None)


def test_bullish_signal_creates_dry_run_order(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session, equity=100_000.0)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()

    assert summary.halted is False
    assert summary.n_buy == 1
    assert summary.n_orders_dry_run == 1
    signals = session.execute(select(Signal)).scalars().all()
    assert len(signals) == 1
    assert signals[0].decision == "BUY"
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1
    assert orders[0].status == "dry_run"
    assert orders[0].side == "buy"
    assert orders[0].qty > 0
    assert orders[0].take_profit is not None
    assert orders[0].stop_price is not None


def test_bearish_score_with_no_position_holds(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()

    assert summary.n_hold == 1
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []


def test_risk_halt_skips_all_processing(session, monkeypatch):
    from packages.shared import config as cfg
    _seed_prediction(session, score=0.9)
    _seed_risk_state(session)
    monkeypatch.setenv("RISK_HALT", "1")
    monkeypatch.setattr(cfg, "_settings", None)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()

    assert summary.halted is True
    assert summary.n_signals == 0
    assert session.execute(select(Signal)).all() == []
    assert session.execute(select(Order)).all() == []


def test_idempotent_rerun_no_duplicate_signals(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()
    runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()

    signals = session.execute(select(Signal)).scalars().all()
    assert len(signals) == 1


def test_alpaca_submission_records_broker_order_id(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.return_value = {"id": "br-123", "status": "accepted"}

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)
    session.flush()

    assert summary.n_orders_submitted == 1
    order = session.execute(select(Order)).scalar_one()
    assert order.broker_order_id == "br-123"
    assert order.status == "accepted"


def test_existing_long_position_holds(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    session.add(
        Position(symbol=symbol, qty=10.0, avg_price=100.0, source="alpaca",
                 updated_at=dt.datetime.now(dt.timezone.utc))
    )
    session.flush()
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    session.flush()

    assert summary.n_hold == 1
    assert session.execute(select(Order)).all() == []


def test_no_predictions_no_error(session):
    summary = runner_mod.run_once(session, model_version="v_missing", alpaca=None)
    assert summary.n_signals == 0
    assert summary.halted is False


def test_valid_sell_against_existing_long_position(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    session.add(
        Position(
            symbol=symbol,
            qty=10.0,
            avg_price=100.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    session.flush()
    _stub_features(monkeypatch, symbol, ts, close=95.0, sma_50=100.0, sent=-0.2)

    alpaca = MagicMock()
    alpaca.submit_market_order.return_value = {"id": "mkt-sell-1", "status": "accepted"}

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)

    assert summary.n_sell == 1
    assert summary.n_orders_submitted == 1
    alpaca.submit_market_order.assert_called_once()
    alpaca.submit_bracket_order.assert_not_called()

    order = session.execute(select(Order)).scalar_one()
    assert order.side == "sell"
    assert order.qty == 10.0
    assert order.broker_order_id == "mkt-sell-1"
    assert order.status == "accepted"
    assert order.take_profit is None
    assert order.stop_price is None


def test_dry_run_sell_against_existing_position(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    session.add(
        Position(
            symbol=symbol,
            qty=25.0,
            avg_price=150.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    session.flush()
    _stub_features(monkeypatch, symbol, ts, close=140.0, sma_50=145.0, sent=-0.15)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_sell == 1
    assert summary.n_orders_dry_run == 1
    order = session.execute(select(Order)).scalar_one()
    assert order.side == "sell"
    assert order.qty == 25.0
    assert order.status == "dry_run"
    assert order.take_profit is None
    assert order.stop_price is None


def test_sell_with_zero_or_negative_position_skips_submission(session, monkeypatch):
    from services.signal.rules import SignalDecision

    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=100.0, sma_50=100.0, sent=-0.1)

    sig = Signal(
        symbol=symbol,
        ts=ts,
        model_version="v1",
        score=0.3,
        decision="SELL",
        rationale={"reason": "exit_on_bearish_score"},
    )
    session.add(sig)
    session.commit()

    decision = SignalDecision(symbol=symbol, decision="SELL", target_pct=0.0, rationale={})
    summary = runner_mod.RunSummary()

    # Call with current_position_qty = 0
    runner_mod._submit_order(  # pylint: disable=protected-access
        session, sig, decision, close=100.0, equity=100_000.0,
        alpaca=None, summary=summary, current_position_qty=0.0,
    )
    assert session.execute(select(Order)).all() == []
    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0

    # Call with negative current_position_qty
    runner_mod._submit_order(  # pylint: disable=protected-access
        session, sig, decision, close=100.0, equity=100_000.0,
        alpaca=None, summary=summary, current_position_qty=-5.0,
    )
    assert session.execute(select(Order)).all() == []


def test_order_intent_persisted_before_broker_submission(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    alpaca = MagicMock()

    # During the broker submission call, check that the order is already in DB as "pending"
    def check_pending_order(*_args, **_kwargs):
        orders = session.execute(select(Order)).scalars().all()
        assert len(orders) == 1
        assert orders[0].status == "pending"
        return {"id": "br-intent", "status": "accepted"}

    alpaca.submit_bracket_order.side_effect = check_pending_order

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)
    assert summary.n_orders_submitted == 1
    order = session.execute(select(Order)).scalar_one()
    assert order.status == "accepted"
    assert order.broker_order_id == "br-intent"


def test_definitive_broker_rejection_marks_order_rejected(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.side_effect = AlpacaError(
        "Alpaca POST /v2/orders returned 422: insufficient buying power",
        status_code=422,
        is_ambiguous=False,
    )

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)

    assert summary.n_orders_submitted == 0
    assert len(summary.errors) == 1
    order = session.execute(select(Order)).scalar_one()
    assert order.status == "rejected"
    assert order.broker_order_id is None


def test_ambiguous_network_timeout_marks_order_unknown(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.side_effect = AlpacaError(
        "Alpaca POST /v2/orders failed: Connection timeout",
        status_code=None,
        is_ambiguous=True,
    )

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)

    assert summary.n_orders_submitted == 0
    assert len(summary.errors) == 1
    order = session.execute(select(Order)).scalar_one()
    assert order.status == "unknown"
    assert order.broker_order_id is None


def test_failure_on_later_symbol_does_not_rollback_earlier_order(session, monkeypatch):
    # Seed 2 symbols
    session.add(Ticker(symbol="AAPL", active=True))
    session.add(Ticker(symbol="MSFT", active=True))
    session.flush()

    ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    session.add(Prediction(symbol="AAPL", ts=ts, model_version="v1", score=0.8, label_pred=1))
    session.add(Prediction(symbol="MSFT", ts=ts, model_version="v1", score=0.8, label_pred=1))
    session.flush()
    _seed_risk_state(session)

    features_df = pd.DataFrame([
        {"symbol": "AAPL", "ts": ts, "close": 150.0, "sma_50": 140.0, "sent_mean_7d": 0.2},
        {"symbol": "MSFT", "ts": ts, "close": 300.0, "sma_50": 280.0, "sent_mean_7d": 0.2},
    ])
    monkeypatch.setattr(runner_mod, "_latest_features", lambda _session: features_df)

    alpaca = MagicMock()

    def fake_submit(symbol, **_kwargs):
        if symbol == "AAPL":
            return {"id": "ord-aapl", "status": "accepted"}
        raise AlpacaError("MSFT failed with 500", status_code=500, is_ambiguous=True)

    alpaca.submit_bracket_order.side_effect = fake_submit

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)

    assert summary.n_orders_submitted == 1
    assert len(summary.errors) == 1

    aapl_order = session.execute(select(Order).where(Order.symbol == "AAPL")).scalar_one()
    assert aapl_order.status == "accepted"
    assert aapl_order.broker_order_id == "ord-aapl"

    msft_order = session.execute(select(Order).where(Order.symbol == "MSFT")).scalar_one()
    assert msft_order.status == "unknown"


def test_repeated_execution_does_not_duplicate_order(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.return_value = {"id": "br-first", "status": "accepted"}

    runner_mod.run_once(session, model_version="v1", alpaca=alpaca)
    # Second execution should not submit another order
    runner_mod.run_once(session, model_version="v1", alpaca=alpaca)

    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1
    assert alpaca.submit_bracket_order.call_count == 1


def test_reconciliation_compatibility_with_sell_order(session):
    from services.broker.reconcile import reconcile_once

    session.add(Ticker(symbol="AAPL", active=True))
    session.add(
        Position(
            symbol="AAPL", qty=10.0, avg_price=150.0, source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    session.add(
        Order(
            symbol="AAPL",
            side="sell",
            qty=10.0,
            order_type="market",
            status="submitted",
            broker_order_id="mkt-sell-rec",
        )
    )
    session.commit()

    alpaca = MagicMock()
    alpaca.get_order.return_value = {
        "status": "filled",
        "filled_qty": "10",
        "filled_avg_price": "155.0",
        "filled_at": "2024-05-02T15:00:00Z",
    }
    alpaca.list_positions.return_value = []  # Closed position
    alpaca.get_account.return_value = {
        "equity": "100000",
        "cash": "100000",
        "long_market_value": "0",
    }

    summary = reconcile_once(session, alpaca)
    assert summary.n_orders_updated == 1
    assert summary.n_new_trades == 1

    order = session.execute(select(Order)).scalar_one()
    assert order.status == "filled"
    assert len(order.trades) == 1
    assert order.trades[0].qty == 10.0
    assert order.trades[0].price == 155.0

    pos = session.get(Position, "AAPL")
    assert pos.qty == 0.0


def test_in_flight_pending_buy_order_prevents_duplicate_buy(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    # In-flight submitted buy order exists, position table has no row
    session.add(
        Order(
            symbol=symbol,
            side="buy",
            qty=10.0,
            order_type="market",
            status="submitted",
            broker_order_id="in-flight-buy-1",
        )
    )
    session.commit()

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_hold == 1
    assert summary.n_buy == 0
    assert summary.n_orders_dry_run == 0

    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1
    assert orders[0].broker_order_id == "in-flight-buy-1"

    signal = session.execute(select(Signal)).scalar_one()
    assert signal.decision == "HOLD"
    assert signal.rationale["reason"] == "hold_existing_position"


def test_in_flight_partially_filled_buy_order_avoids_double_counting(session, monkeypatch):
    from packages.shared.models import Trade

    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    # 4 shares already held in Position
    session.add(
        Position(
            symbol=symbol,
            qty=4.0,
            avg_price=100.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    # Order for 10 shares, 4 filled, 6 remaining unfilled
    order = Order(
        symbol=symbol,
        side="buy",
        qty=10.0,
        order_type="market",
        status="partially_filled",
        broker_order_id="part-fill-1",
    )
    session.add(order)
    session.commit()

    session.add(
        Trade(
            order_id=order.id,
            ts=dt.datetime.now(dt.timezone.utc),
            qty=4.0,
            price=100.0,
            broker_trade_id="trade-1",
        )
    )
    session.commit()

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_hold == 1
    assert summary.n_buy == 0

    signal = session.execute(select(Signal)).scalar_one()
    assert signal.decision == "HOLD"
    assert signal.rationale["reason"] == "hold_existing_position"


def test_canceled_and_rejected_orders_do_not_block_buy(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.7)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=110.0, sma_50=100.0, sent=0.1)

    # Previous orders were canceled and rejected
    session.add(
        Order(
            symbol=symbol,
            side="buy",
            qty=10.0,
            order_type="market",
            status="canceled",
            broker_order_id="old-canceled",
        )
    )
    session.add(
        Order(
            symbol=symbol,
            side="buy",
            qty=10.0,
            order_type="market",
            status="rejected",
            broker_order_id="old-rejected",
        )
    )
    session.commit()

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_buy == 1
    assert summary.n_orders_dry_run == 1
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 3


def test_in_flight_buy_orders_count_towards_max_exposure_cap(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.8)
    session.add(Ticker(symbol="MSFT", active=True))
    session.flush()

    # Base equity 100k, exposure already at 76%
    session.add(
        RiskState(
            ts=dt.datetime.now(dt.timezone.utc),
            equity=100_000.0,
            cash=24_000.0,
            exposure_pct=76.0,
            n_open_positions=1,
            halted=False,
        )
    )
    # In-flight buy order for MSFT: 40 shares at $100 = $4,000 = 4% of 100k
    session.add(
        Order(
            symbol="MSFT",
            side="buy",
            qty=40.0,
            order_type="market",
            status="submitted",
            broker_order_id="msft-inflight",
        )
    )
    session.commit()

    features_df = pd.DataFrame([
        {"symbol": symbol, "ts": ts, "close": 100.0, "sma_50": 90.0, "sent_mean_7d": 0.2},
        {"symbol": "MSFT", "ts": ts, "close": 100.0, "sma_50": 90.0, "sent_mean_7d": 0.2},
    ])
    monkeypatch.setattr(runner_mod, "_latest_features", lambda _session: features_df)

    # 76% base + 4% in-flight = 80%. Target 5% would breach max 80% exposure cap.
    summary = runner_mod.run_once(
        session, model_version="v1", alpaca=None,
        target_pct=5.0, max_exposure_pct=80.0,
    )

    assert summary.n_buy == 0
    assert summary.n_hold == 1

    signal = session.execute(select(Signal).where(Signal.symbol == symbol)).scalar_one()
    assert signal.decision == "HOLD"
    assert signal.rationale["reason"] == "exposure_cap_reached"


def test_in_flight_buy_orders_count_towards_max_positions_cap(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.8)
    session.add(Ticker(symbol="MSFT", active=True))
    session.add(Ticker(symbol="GOOG", active=True))
    session.flush()

    _seed_risk_state(session)

    # Position 1: held MSFT
    session.add(
        Position(
            symbol="MSFT",
            qty=10.0,
            avg_price=100.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    # Position 2: in-flight buy for GOOG
    session.add(
        Order(
            symbol="GOOG",
            side="buy",
            qty=10.0,
            order_type="market",
            status="submitted",
            broker_order_id="goog-inflight",
        )
    )
    session.commit()

    features_df = pd.DataFrame([
        {"symbol": symbol, "ts": ts, "close": 100.0, "sma_50": 90.0, "sent_mean_7d": 0.2},
        {"symbol": "MSFT", "ts": ts, "close": 100.0, "sma_50": 90.0, "sent_mean_7d": 0.2},
        {"symbol": "GOOG", "ts": ts, "close": 100.0, "sma_50": 90.0, "sent_mean_7d": 0.2},
    ])
    monkeypatch.setattr(runner_mod, "_latest_features", lambda _session: features_df)

    # max_positions=2. Currently 1 held + 1 in-flight = 2. AAPL should be held due to max positions reached.
    summary = runner_mod.run_once(
        session, model_version="v1", alpaca=None, max_positions=2,
    )

    assert summary.n_buy == 0
    assert summary.n_hold == 1

    signal = session.execute(select(Signal).where(Signal.symbol == symbol)).scalar_one()
    assert signal.decision == "HOLD"
    assert signal.rationale["reason"] == "max_positions_reached"


def test_in_flight_sell_order_prevents_duplicate_sell(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    session.add(
        Position(
            symbol=symbol,
            qty=10.0,
            avg_price=100.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    session.add(
        Order(
            symbol=symbol,
            side="sell",
            qty=10.0,
            order_type="market",
            status="submitted",
            broker_order_id="sell-inflight-1",
        )
    )
    session.commit()

    _stub_features(monkeypatch, symbol, ts, close=90.0, sma_50=100.0, sent=-0.2)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_sell == 0
    assert summary.n_hold == 1
    # No new orders created
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1


def test_in_flight_buy_does_not_permit_selling_unfilled_shares(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    # Only in-flight buy exists, no position held
    session.add(
        Order(
            symbol=symbol,
            side="buy",
            qty=10.0,
            order_type="market",
            status="submitted",
            broker_order_id="buy-inflight-1",
        )
    )
    session.commit()

    _stub_features(monkeypatch, symbol, ts, close=90.0, sma_50=100.0, sent=-0.2)

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)

    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1


def test_stale_prediction_skips_order_submission(session, monkeypatch):
    pred_ts = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    # as_of is 9 days later
    as_of = dt.datetime(2024, 5, 10, 16, 0, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
    )

    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []
    assert any("stale_prediction" in err for err in summary.errors)


def test_stale_prediction_trading_day_limit(session, monkeypatch):
    # Friday evaluated Wednesday in normal week (3 trading days elapsed)
    pred_ts = dt.datetime(2024, 5, 3, 20, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    as_of = dt.datetime(2024, 5, 8, 20, 0, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
        max_trading_days=1,
    )

    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    assert any("stale_prediction" in err for err in summary.errors)


def test_future_dated_prediction_skips_order_submission(session, monkeypatch):
    pred_ts = dt.datetime(2024, 5, 5, 16, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    as_of = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
    )

    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []
    assert any("future_dated_prediction" in err for err in summary.errors)


def test_missing_timestamp_prediction_skips_order_submission(session, monkeypatch):
    _seed_risk_state(session)
    fake_preds = pd.DataFrame([
        {"symbol": "AAPL", "ts": None, "score": 0.8, "model_version": "v1"}
    ])
    monkeypatch.setattr(runner_mod, "_latest_predictions", lambda _s, _m: fake_preds)
    _stub_features(
        monkeypatch, "AAPL", dt.datetime(2024, 5, 1), close=150.0, sma_50=140.0, sent=0.2
    )

    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []


def test_mismatched_model_version_skips_order_submission(session, monkeypatch):
    pred_ts = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts, model_version="v2")
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    # When runner is looking for v1, v2 is not returned or fails validation
    summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []


def test_empty_model_version_fails_safely(session):
    summary = runner_mod.run_once(session, model_version="", alpaca=None)
    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    assert any("invalid_model_version" in err for err in summary.errors)


def test_weekend_market_closure_preserves_prediction_freshness(session, monkeypatch):
    # Friday 2024-05-03 evaluated Monday 2024-05-06 morning (1 trading day elapsed)
    pred_ts = dt.datetime(2024, 5, 3, 20, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    as_of = dt.datetime(2024, 5, 6, 13, 30, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
        max_trading_days=1,
    )

    assert summary.n_buy == 1
    assert summary.n_orders_dry_run == 1
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1
    assert orders[0].symbol == "AAPL"


def test_holiday_weekend_preserves_prediction_freshness(session, monkeypatch):
    # Friday 2024-05-24 evaluated Tuesday 2024-05-28 morning (Memorial Day holiday on Mon)
    pred_ts = dt.datetime(2024, 5, 24, 20, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    as_of = dt.datetime(2024, 5, 28, 13, 30, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
        max_trading_days=1,
    )

    assert summary.n_buy == 1
    assert summary.n_orders_dry_run == 1
    orders = session.execute(select(Order)).scalars().all()
    assert len(orders) == 1
    assert orders[0].symbol == "AAPL"


def test_prediction_lagging_behind_latest_price_bar_skips_order(session, monkeypatch):
    pred_ts = dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc)
    symbol, ts = _seed_prediction(session, symbol="AAPL", score=0.8, ts=pred_ts)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    # Insert a newer price bar for AAPL
    from packages.shared.models import PriceBar
    session.add(
        PriceBar(
            symbol=symbol,
            ts=dt.datetime(2024, 5, 2, 16, 0, tzinfo=dt.timezone.utc),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=100000.0,
            source="test",
        )
    )
    session.commit()

    as_of = dt.datetime(2024, 5, 1, 16, 30, tzinfo=dt.timezone.utc)
    summary = runner_mod.run_once(
        session,
        model_version="v1",
        alpaca=None,
        as_of=as_of,
    )

    assert summary.n_orders_submitted == 0
    assert summary.n_orders_dry_run == 0
    orders = session.execute(select(Order)).scalars().all()
    assert orders == []
    assert any("lags behind latest price bar" in err for err in summary.errors)


def test_advisory_lock_contention_skips_second_execution(session, monkeypatch):
    from packages.shared.db import run_signals_lock
    symbol, ts = _seed_prediction(session, score=0.8)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    with run_signals_lock(session.get_bind()) as acquired:
        assert acquired is True
        summary = runner_mod.run_once(session, model_version="v1", alpaca=None)
        assert summary.n_orders_dry_run == 0
        assert summary.n_orders_submitted == 0
        assert any("run_signals_locked" in err for err in summary.errors)


def test_advisory_lock_released_after_exception(session, monkeypatch):
    from packages.shared.db import run_signals_lock
    _seed_prediction(session, score=0.8)
    _seed_risk_state(session)

    monkeypatch.setattr(runner_mod, "_latest_predictions", MagicMock(side_effect=RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        runner_mod.run_once(session, model_version="v1", alpaca=None)

    with run_signals_lock(session.get_bind()) as acquired:
        assert acquired is True


def test_duplicate_non_null_signal_id_rejected_by_database(session):
    from sqlalchemy.exc import IntegrityError
    session.add(Ticker(symbol="AAPL", active=True))
    session.commit()

    sig = Signal(
        symbol="AAPL",
        ts=dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc),
        model_version="v1",
        score=0.8,
        decision="BUY",
        rationale={"test": True},
    )
    session.add(sig)
    session.commit()

    order1 = Order(
        symbol="AAPL",
        side="buy",
        qty=10.0,
        status="pending",
        signal_id=sig.id,
    )
    session.add(order1)
    session.commit()

    order2 = Order(
        symbol="AAPL",
        side="buy",
        qty=10.0,
        status="pending",
        signal_id=sig.id,
    )
    session.add(order2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_multiple_orders_with_null_signal_id_permitted(session):
    session.add(Ticker(symbol="AAPL", active=True))
    session.commit()

    order1 = Order(
        symbol="AAPL",
        side="buy",
        qty=10.0,
        status="pending",
        signal_id=None,
    )
    order2 = Order(
        symbol="AAPL",
        side="buy",
        qty=15.0,
        status="pending",
        signal_id=None,
    )
    session.add(order1)
    session.add(order2)
    session.commit()

    orders = session.execute(select(Order).where(Order.signal_id.is_(None))).scalars().all()
    assert len(orders) >= 2


def test_integrity_error_recovery_leaves_session_usable(session):
    from sqlalchemy.exc import IntegrityError
    session.add(Ticker(symbol="AAPL", active=True))
    session.commit()

    sig = Signal(
        symbol="AAPL",
        ts=dt.datetime(2024, 5, 1, 16, 0, tzinfo=dt.timezone.utc),
        model_version="v1",
        score=0.8,
        decision="BUY",
        rationale={"test": True},
    )
    session.add(sig)
    session.commit()

    session.add(Order(symbol="AAPL", side="buy", qty=10.0, signal_id=sig.id))
    session.commit()

    session.add(Order(symbol="AAPL", side="buy", qty=10.0, signal_id=sig.id))
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    refreshed_sig = session.execute(select(Signal).where(Signal.id == sig.id)).scalar_one()
    assert refreshed_sig.symbol == "AAPL"


def test_deterministic_client_order_id_generation(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.8)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.return_value = {"id": "brk-101", "status": "submitted"}

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)
    assert summary.n_orders_submitted == 1

    signal_row = session.execute(select(Signal).where(Signal.symbol == symbol)).scalar_one()
    expected_client_order_id = f"sp-sig-{signal_row.id}"
    alpaca.submit_bracket_order.assert_called_once()
    call_kwargs = alpaca.submit_bracket_order.call_args.kwargs
    assert call_kwargs["client_order_id"] == expected_client_order_id


def test_duplicate_alpaca_client_order_id_requires_reconciliation(session, monkeypatch):
    symbol, ts = _seed_prediction(session, score=0.8)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    alpaca = MagicMock()
    alpaca.submit_bracket_order.side_effect = AlpacaError(
        "client_order_id must be unique", status_code=422, is_duplicate=True, is_ambiguous=True
    )
    alpaca.get_order_by_client_id.return_value = {
        "id": "alpaca-existing-99",
        "status": "accepted",
    }

    summary = runner_mod.run_once(session, model_version="v1", alpaca=alpaca)
    assert summary.n_orders_submitted == 0
    assert any("duplicate_client_order_id" in err for err in summary.errors)

    order = session.execute(select(Order)).scalar_one()
    assert order.broker_order_id == "alpaca-existing-99"
    assert order.status == "accepted"


def test_concurrent_buy_executions_do_not_duplicate_orders(session, monkeypatch):
    import concurrent.futures
    from packages.shared.db import get_sessionmaker
    symbol, ts = _seed_prediction(session, score=0.8)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=150.0, sma_50=140.0, sent=0.2)

    session_factory = get_sessionmaker()

    def run_worker():
        worker_session = session_factory()
        try:
            return runner_mod.run_once(worker_session, model_version="v1", alpaca=None)
        finally:
            worker_session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_worker)
        f2 = executor.submit(run_worker)
        s1 = f1.result()
        s2 = f2.result()

    total_dry_run = s1.n_orders_dry_run + s2.n_orders_dry_run
    assert total_dry_run == 1
    orders = session.execute(select(Order).where(Order.symbol == symbol)).scalars().all()
    assert len(orders) == 1


def test_concurrent_sell_executions_do_not_duplicate_orders(session, monkeypatch):
    import concurrent.futures
    from packages.shared.db import get_sessionmaker
    symbol, ts = _seed_prediction(session, score=0.3)
    _seed_risk_state(session)
    _stub_features(monkeypatch, symbol, ts, close=90.0, sma_50=100.0, sent=-0.2)

    session.add(
        Position(
            symbol=symbol,
            qty=10.0,
            avg_price=100.0,
            source="alpaca",
            updated_at=dt.datetime.now(dt.timezone.utc),
        )
    )
    session.commit()

    session_factory = get_sessionmaker()

    def run_worker():
        worker_session = session_factory()
        try:
            return runner_mod.run_once(worker_session, model_version="v1", alpaca=None)
        finally:
            worker_session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_worker)
        f2 = executor.submit(run_worker)
        s1 = f1.result()
        s2 = f2.result()

    total_sells = s1.n_orders_dry_run + s2.n_orders_dry_run
    assert total_sells == 1
    orders = session.execute(select(Order).where(Order.symbol == symbol)).scalars().all()
    assert len(orders) == 1
    assert orders[0].side == "sell"


def test_concurrent_buy_decisions_respect_portfolio_capacity(session, monkeypatch):
    import concurrent.futures
    from packages.shared.db import get_sessionmaker
    sym_a, ts_a = _seed_prediction(session, symbol="AAPL", score=0.8)
    for i in range(19):
        sym_dummy = f"DUM{i:02d}"
        session.add(Ticker(symbol=sym_dummy, active=True))
        session.add(
            Position(
                symbol=sym_dummy,
                qty=10.0,
                avg_price=50.0,
                source="alpaca",
                updated_at=dt.datetime.now(dt.timezone.utc),
            )
        )
    _seed_risk_state(session)
    _stub_features(monkeypatch, sym_a, ts_a, close=150.0, sma_50=140.0, sent=0.2)

    session_factory = get_sessionmaker()

    def run_worker():
        worker_session = session_factory()
        try:
            return runner_mod.run_once(
                worker_session,
                model_version="v1",
                alpaca=None,
                max_positions=20,
            )
        finally:
            worker_session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_worker)
        f2 = executor.submit(run_worker)
        s1 = f1.result()
        s2 = f2.result()

    total_new_buys = s1.n_orders_dry_run + s2.n_orders_dry_run
    assert total_new_buys == 1
    orders = session.execute(select(Order).where(Order.symbol == sym_a)).scalars().all()
    assert len(orders) == 1
