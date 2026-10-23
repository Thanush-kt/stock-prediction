"""FastAPI app factory for the Phase 3.5 dashboard shim."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.deps import get_current_user
from services.api.routers import equity, health, orders, positions, predictions, signals, stocks


def create_app() -> FastAPI:
    application = FastAPI(
        title="Stock-Prediction Dashboard API",
        version="0.1.0",
        description="Read-only shim feeding the Next.js dashboard.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    # Public liveness probe
    application.include_router(health.router, tags=["health"])

    # Protected routes requiring verified Clerk session token
    application.include_router(
        positions.router, tags=["positions"], dependencies=[Depends(get_current_user)]
    )
    application.include_router(
        signals.router, tags=["signals"], dependencies=[Depends(get_current_user)]
    )
    application.include_router(
        orders.router, tags=["orders"], dependencies=[Depends(get_current_user)]
    )
    application.include_router(
        equity.router, tags=["equity"], dependencies=[Depends(get_current_user)]
    )
    application.include_router(
        predictions.router, tags=["predictions"], dependencies=[Depends(get_current_user)]
    )
    application.include_router(
        stocks.router, tags=["stocks"], dependencies=[Depends(get_current_user)]
    )
    return application


app = create_app()
