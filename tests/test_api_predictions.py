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


def test_predictions_latest(client, session):
    _seed(session)
    resp = client.get("/predictions/latest")
    assert resp.status_code == 200
    data = resp.json()
    # Should return 1 latest row for AAPL (v1) and 1 for MSFT (v2)
    assert len(data) == 2
    symbols = {d["symbol"] for d in data}
    assert symbols == {"AAPL", "MSFT"}
    aapl = next(d for d in data if d["symbol"] == "AAPL")
    assert aapl["score"] == 0.82  # latest AAPL score from 2024-05-02


def test_predictions_latest_filter_symbol(client, session):
    _seed(session)
    resp = client.get("/predictions/latest", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"
    assert data[0]["score"] == 0.82


def test_predictions_accuracy(client, session):
    session.add(Ticker(symbol="NVDA", active=True))
    today = dt.datetime.now(dt.timezone.utc).date()
    p1 = Prediction(
        symbol="NVDA",
        ts=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2),
        target_session=today - dt.timedelta(days=1),
        model_version="v1",
        score=0.9,
        label_pred=1,
        actual_label=1,
    )
    p2 = Prediction(
        symbol="NVDA",
        ts=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3),
        target_session=today - dt.timedelta(days=2),
        model_version="v1",
        score=0.2,
        label_pred=0,
        actual_label=1,  # miss
    )
    session.add_all([p1, p2])
    session.commit()

    resp = client.get("/predictions/accuracy", params={"symbol": "NVDA"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "NVDA"
    assert data[0]["n_evaluated"] == 2
    assert data[0]["n_correct"] == 1
    assert data[0]["accuracy"] == 0.5


def test_predictions_sessions_endpoint(client, session):
    session.add(Ticker(symbol="AAPL", active=True))
    session.add(Ticker(symbol="RELIANCE.NS", active=True))
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    tomorrow = today + dt.timedelta(days=1)

    p_today = Prediction(
        symbol="AAPL",
        ts=now - dt.timedelta(days=1),
        target_session=today,
        data_cutoff_ts=now - dt.timedelta(days=1),
        model_version="v1",
        score=0.72,
        label_pred=1,
    )
    p_tomorrow = Prediction(
        symbol="RELIANCE.NS",
        ts=now - dt.timedelta(days=1),
        target_session=tomorrow,
        data_cutoff_ts=now - dt.timedelta(days=1),
        model_version="v1",
        score=0.35,
        label_pred=0,
    )
    session.add_all([p_today, p_tomorrow])
    session.commit()

    resp = client.get("/predictions/sessions", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    aapl_data = data[0]
    assert aapl_data["symbol"] == "AAPL"
    assert aapl_data["exchange"] == "NYSE"
    assert "today" in aapl_data
    assert "tomorrow" in aapl_data
    assert aapl_data["today"]["target_session"] == today.isoformat()
    assert aapl_data["today"]["prediction"]["score"] == 0.72
    assert aapl_data["today"]["prediction"]["label_pred"] == 1


def test_predictions_sessions_filter_symbol(client, session):
    session.add(Ticker(symbol="MSFT", active=True))
    session.commit()
    resp = client.get("/predictions/sessions", params={"symbol": "MSFT"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "MSFT"
    assert data[0]["today"]["status"] in ("available", "unavailable", "stale")
    assert data[0]["tomorrow"]["status"] in ("available", "pending_close", "unavailable")


