"""Tests for GET /stocks endpoints."""
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from packages.shared.models import Indicator, PriceBar, Ticker
from services.api.deps import ClerkUser, get_current_user, get_session
from services.api.main import app


@pytest.fixture(name="client")
def fixture_client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: ClerkUser(user_id="test_user")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_stocks(client, session):
    session.add(Ticker(symbol="AAPL", name="Apple Inc.", active=True))
    session.add(Ticker(symbol="RELIANCE.NS", name="Reliance Industries", active=True))
    session.add(Ticker(symbol="BTC-USD", name="Bitcoin", active=True))
    session.add(Ticker(symbol="INACTIVE", name="Inactive Ticker", active=False))
    session.commit()

    resp = client.get("/stocks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3  # active_only=True by default

    aapl = next(s for s in data if s["symbol"] == "AAPL")
    assert aapl["exchange"] == "NYSE"
    assert aapl["asset_class"] == "equity"

    reliance = next(s for s in data if s["symbol"] == "RELIANCE.NS")
    assert reliance["exchange"] == "NSE"
    assert reliance["asset_class"] == "equity"

    btc = next(s for s in data if s["symbol"] == "BTC-USD")
    assert btc["exchange"] == "CRYPTO"
    assert btc["asset_class"] == "crypto"


def test_stock_market_data_fallback_db(client, session):
    session.add(Ticker(symbol="TEST.TICKER", active=True))
    now = dt.datetime.now(dt.timezone.utc)
    bar = PriceBar(
        symbol="TEST.TICKER",
        ts=now,
        open=400.0,
        high=405.0,
        low=398.0,
        close=402.5,
        volume=1000000.0,
        source="test",
    )
    session.add(bar)
    session.commit()

    resp = client.get("/stocks/TEST.TICKER/market-data")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TEST.TICKER"
    assert data["price"] == 402.5


def test_stock_market_data_not_found(client, session):
    resp = client.get("/stocks/NONEXISTENT_TICKER_12345/market-data")
    assert resp.status_code == 404


def test_stock_price_history(client, session):
    session.add(Ticker(symbol="AAPL", active=True))
    now = dt.datetime.now(dt.timezone.utc)
    for i in range(5):
        session.add(
            PriceBar(
                symbol="AAPL",
                ts=now - dt.timedelta(days=i),
                open=150.0 + i,
                high=155.0 + i,
                low=149.0 + i,
                close=152.0 + i,
                volume=500000.0,
                source="test",
            )
        )
    session.commit()

    resp = client.get("/stocks/AAPL/price-history", params={"days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    # Should be ordered ascending by ts
    assert data[0]["ts"] < data[-1]["ts"]


def test_stock_risk_analysis(client, session):
    session.add(Ticker(symbol="AAPL", active=True))
    now = dt.datetime.now(dt.timezone.utc)
    # Add 30 bars so volatility can be computed
    for i in range(30):
        session.add(
            PriceBar(
                symbol="AAPL",
                ts=now - dt.timedelta(days=30 - i),
                open=150.0 + (i % 5),
                high=155.0 + (i % 5),
                low=148.0 + (i % 5),
                close=150.0 + (i % 5) * 1.5,
                volume=1000000.0,
                source="test",
            )
        )
    session.add(
        Indicator(
            symbol="AAPL",
            ts=now,
            name="atr_14",
            value=3.25,
        )
    )
    session.commit()

    resp = client.get("/stocks/AAPL/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["atr_14"] == 3.25
    assert data["hist_volatility_20d"] is not None
    assert data["stop_loss_pct"] == 0.02
    assert data["take_profit_pct"] == 0.04
    assert data["risk_reward_ratio"] == 2.0
    assert data["risk_category"] in ("LOW", "MEDIUM", "HIGH", "VERY HIGH")
