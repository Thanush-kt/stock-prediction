"""Outcome evaluation for predictions.

Compares predictions whose target_session has passed against actual
closing prices recorded in price_bars, populating actual_close,
actual_label, and evaluated_at.
"""
from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy import cast, select
from sqlalchemy.orm import Session

from packages.shared.logging import get_logger
from packages.shared.models import Prediction, PriceBar

log = get_logger(__name__)


def evaluate_outcomes(
    session: Session,
    as_of: dt.date | None = None,
    symbol: str | None = None,
    model_version: str | None = None,
) -> int:
    """Evaluate past predictions whose target trading session has completed.

    For each prediction where target_session <= as_of and actual_label is NULL:
      - Look up the actual close on target_session.
      - Look up the cutoff close on ts (data_cutoff_ts).
      - Set actual_label = 1 if target close > cutoff close else 0.
      - Set evaluated_at to UTC now.

    Returns the count of evaluated predictions.
    """
    cutoff_date = as_of or dt.datetime.now(dt.timezone.utc).date()

    query = select(Prediction).where(
        Prediction.target_session.is_not(None),
        Prediction.target_session <= cutoff_date,
        Prediction.actual_label.is_(None),
    )
    if symbol:
        query = query.where(Prediction.symbol == symbol.upper())
    if model_version:
        query = query.where(Prediction.model_version == model_version)

    pending_predictions = session.execute(query).scalars().all()
    if not pending_predictions:
        log.info("No unevaluated predictions due on or before %s", cutoff_date)
        return 0

    evaluated_count = 0
    now_utc = dt.datetime.now(dt.timezone.utc)

    for pred in pending_predictions:
        # 1. Fetch the target session bar within the calendar day
        start_of_target = dt.datetime.combine(pred.target_session, dt.time.min).replace(
            tzinfo=dt.timezone.utc
        )
        end_of_target = dt.datetime.combine(pred.target_session, dt.time.max).replace(
            tzinfo=dt.timezone.utc
        )
        target_bar = session.execute(
            select(PriceBar)
            .where(
                PriceBar.symbol == pred.symbol,
                PriceBar.ts >= start_of_target,
                PriceBar.ts <= end_of_target,
            )
            .order_by(PriceBar.ts.desc())
            .limit(1)
        ).scalar_one_or_none()

        if target_bar is None:
            # Market data for target_session might not have been ingested yet
            continue

        # 2. Fetch the cutoff bar (baseline close)
        cutoff_ts = pred.data_cutoff_ts or pred.ts
        cutoff_bar = session.execute(
            select(PriceBar).where(
                PriceBar.symbol == pred.symbol,
                PriceBar.ts == cutoff_ts,
            )
        ).scalar_one_or_none()

        if cutoff_bar is None:
            # Fallback: find nearest bar on or before cutoff_ts
            cutoff_bar = session.execute(
                select(PriceBar)
                .where(
                    PriceBar.symbol == pred.symbol,
                    PriceBar.ts <= cutoff_ts,
                )
                .order_by(PriceBar.ts.desc())
                .limit(1)
            ).scalar_one_or_none()

        if cutoff_bar is None:
            continue

        pred.actual_close = float(target_bar.close)
        pred.actual_label = 1 if target_bar.close > cutoff_bar.close else 0
        pred.evaluated_at = now_utc
        evaluated_count += 1

    session.flush()
    log.info(
        "evaluate_outcomes: evaluated %d of %d pending predictions (cutoff %s)",
        evaluated_count,
        len(pending_predictions),
        cutoff_date,
    )
    return evaluated_count
