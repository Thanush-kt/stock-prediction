"""Tests for prediction outcome evaluation (services/model/evaluate.py)."""
from __future__ import annotations

import datetime as dt

from packages.shared.models import Prediction, PriceBar, Ticker
from services.model.evaluate import evaluate_outcomes


def test_evaluate_outcomes_successful(session):
    session.add(Ticker(symbol="AAPL", active=True))
    session.add(Ticker(symbol="MSFT", active=True))
    session.flush()

    today = dt.date(2024, 5, 10)
    cutoff_ts_aapl = dt.datetime(2024, 5, 8, 20, 0, tzinfo=dt.timezone.utc)
    target_date_aapl = dt.date(2024, 5, 9)

    cutoff_ts_msft = dt.datetime(2024, 5, 8, 20, 0, tzinfo=dt.timezone.utc)
    target_date_msft = dt.date(2024, 5, 9)

    # Cutoff bars
    session.add(
        PriceBar(
            symbol="AAPL",
            ts=cutoff_ts_aapl,
            open=180.0,
            high=182.0,
            low=179.0,
            close=180.0,
            volume=100000.0,
            source="test",
        )
    )
    session.add(
        PriceBar(
            symbol="MSFT",
            ts=cutoff_ts_msft,
            open=400.0,
            high=402.0,
            low=398.0,
            close=400.0,
            volume=100000.0,
            source="test",
        )
    )

    # Realized target session bars
    session.add(
        PriceBar(
            symbol="AAPL",
            ts=dt.datetime(2024, 5, 9, 20, 0, tzinfo=dt.timezone.utc),
            open=181.0,
            high=186.0,
            low=180.0,
            close=185.0,  # 185 > 180 -> actual_label = 1
            volume=100000.0,
            source="test",
        )
    )
    session.add(
        PriceBar(
            symbol="MSFT",
            ts=dt.datetime(2024, 5, 9, 20, 0, tzinfo=dt.timezone.utc),
            open=400.0,
            high=401.0,
            low=390.0,
            close=395.0,  # 395 < 400 -> actual_label = 0
            volume=100000.0,
            source="test",
        )
    )

    # Predictions
    pred_aapl = Prediction(
        symbol="AAPL",
        ts=cutoff_ts_aapl,
        target_session=target_date_aapl,
        data_cutoff_ts=cutoff_ts_aapl,
        model_version="v1",
        score=0.8,
        label_pred=1,
    )
    pred_msft = Prediction(
        symbol="MSFT",
        ts=cutoff_ts_msft,
        target_session=target_date_msft,
        data_cutoff_ts=cutoff_ts_msft,
        model_version="v1",
        score=0.2,
        label_pred=0,
    )
    session.add_all([pred_aapl, pred_msft])
    session.commit()

    count = evaluate_outcomes(session, as_of=today)
    assert count == 2

    session.refresh(pred_aapl)
    session.refresh(pred_msft)

    assert pred_aapl.actual_close == 185.0
    assert pred_aapl.actual_label == 1
    assert pred_aapl.evaluated_at is not None

    assert pred_msft.actual_close == 395.0
    assert pred_msft.actual_label == 0
    assert pred_msft.evaluated_at is not None


def test_evaluate_outcomes_skips_future_sessions(session):
    session.add(Ticker(symbol="NVDA", active=True))
    today = dt.date(2024, 5, 10)
    future_date = dt.date(2024, 5, 15)

    pred = Prediction(
        symbol="NVDA",
        ts=dt.datetime(2024, 5, 10, 20, 0, tzinfo=dt.timezone.utc),
        target_session=future_date,
        model_version="v1",
        score=0.7,
        label_pred=1,
    )
    session.add(pred)
    session.commit()

    count = evaluate_outcomes(session, as_of=today)
    assert count == 0
    session.refresh(pred)
    assert pred.actual_label is None
