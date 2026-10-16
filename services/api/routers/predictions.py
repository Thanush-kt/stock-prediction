"""GET /predictions — recent model predictions, optionally filtered by symbol or model_version."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.shared.models import Prediction
from services.api.deps import get_session
from services.api.schemas import PredictionOut

router = APIRouter()


@router.get("/predictions", response_model=list[PredictionOut])
def list_predictions(
    limit: int = Query(50, ge=1, le=500),
    symbol: str | None = None,
    model_version: str | None = None,
    session: Session = Depends(get_session),
) -> list[PredictionOut]:
    stmt = select(Prediction).order_by(Prediction.ts.desc(), Prediction.id.desc()).limit(limit)
    if symbol is not None:
        stmt = stmt.where(Prediction.symbol == symbol.upper())
    if model_version is not None:
        stmt = stmt.where(Prediction.model_version == model_version)
    rows = session.execute(stmt).scalars().all()
    return [PredictionOut.model_validate(r) for r in rows]
