"""GET /predictions tests."""
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from packages.shared.models import Prediction, Ticker
from services.api.deps import ClerkUser, get_current_user, get_session
from services.api.main import app


@pytest.fixture(name="client")
def fixture_client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: ClerkUser(user_id="test_user")
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed(session):
    session.add(Ticker(symbol="AAPL", active=True))
    session.add(Ticker(symbol="MSFT", active=True))
    session.flush()

    preds = [
        Prediction(
            symbol="AAPL",
            ts=dt.datetime(2024, 5, 1, tzinfo=dt.timezone.utc),
            model_version="v1",
            score=0.75,
            label_pred=1,
        ),
        Prediction(
            symbol="AAPL",
            ts=dt.datetime(2024, 5, 2, tzinfo=dt.timezone.utc),
            model_version="v1",
            score=0.82,
            label_pred=1,
        ),
        Prediction(
            symbol="MSFT",
            ts=dt.datetime(2024, 5, 3, tzinfo=dt.timezone.utc),
            model_version="v2",
            score=0.35,
            label_pred=0,
        ),
    ]
    session.add_all(preds)
    session.commit()


def test_list_predictions_empty(client):
    resp = client.get("/predictions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_predictions_ordering(client, session):
    _seed(session)
    resp = client.get("/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Ordered by ts descending
    assert data[0]["symbol"] == "MSFT"
    assert data[1]["symbol"] == "AAPL"
    assert data[1]["score"] == 0.82
    assert data[2]["symbol"] == "AAPL"
    assert data[2]["score"] == 0.75


def test_list_predictions_filter_by_symbol(client, session):
    _seed(session)
    resp = client.get("/predictions", params={"symbol": "msft"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "MSFT"
    assert data[0]["label_pred"] == 0


def test_list_predictions_filter_by_model_version(client, session):
    _seed(session)
    resp = client.get("/predictions", params={"model_version": "v1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(p["model_version"] == "v1" for p in data)


def test_list_predictions_limit(client, session):
    _seed(session)
    resp = client.get("/predictions", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
