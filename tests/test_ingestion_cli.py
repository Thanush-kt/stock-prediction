"""Regression tests for services.ingestion.cli (OptionInfo bug & CLI pipeline)."""
from __future__ import annotations

import datetime as dt

import pytest
from typer.testing import CliRunner

from services.ingestion import cli as ingestion_cli

runner = CliRunner()


def test_parse_symbols_with_none(monkeypatch):
    monkeypatch.setattr(ingestion_cli, "_watchlist", lambda: ["AAPL", "MSFT"])
    assert ingestion_cli.parse_symbols(None) == ["AAPL", "MSFT"]


def test_parse_symbols_with_string():
    assert ingestion_cli.parse_symbols("aapl, msft , nvda ") == ["AAPL", "MSFT", "NVDA"]


def test_parse_symbols_with_sequence():
    assert ingestion_cli.parse_symbols(["aapl", "tsla"]) == ["AAPL", "TSLA"]


def test_parse_symbols_with_option_info_fallback(monkeypatch):
    """OptionInfo object passed inadvertently via direct Python invocation must not fail."""
    import typer
    option_obj = typer.Option(None)
    monkeypatch.setattr(ingestion_cli, "_watchlist", lambda: ["AAPL", "NVDA"])
    # Should safely return fallback watchlist without raising AttributeError: 'OptionInfo' object has no attribute 'split'
    result = ingestion_cli.parse_symbols(option_obj)
    assert result == ["AAPL", "NVDA"]


def test_direct_python_invocation_run_daily(monkeypatch):
    """Directly calling run_daily() in Python must not trigger OptionInfo AttributeError."""
    calls = []

    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_prices",
        lambda since, symbols: calls.append(("prices", since, symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_compute_features",
        lambda symbols: calls.append(("features", symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_news",
        lambda symbols: calls.append(("news", symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_score_sentiment",
        lambda: calls.append(("sentiment",)),
    )

    # Calling directly without passing symbols (exact bug trigger)
    ingestion_cli.run_daily(since="2023-01-01")

    assert len(calls) == 4
    assert calls[0] == ("prices", "2023-01-01", None)
    assert calls[1] == ("features", None)
    assert calls[2] == ("news", None)
    assert calls[3] == ("sentiment",)


def test_direct_python_invocation_ingest_prices(monkeypatch):
    """Directly calling ingest_prices() in Python without passing symbols must succeed."""
    called = []
    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_prices",
        lambda since, symbols: called.append((since, symbols)),
    )

    ingestion_cli.ingest_prices(since="2024-05-01")
    assert called == [("2024-05-01", None)]


def test_direct_python_invocation_compute_features(monkeypatch):
    """Directly calling compute_features() in Python without passing symbols must succeed."""
    called = []
    monkeypatch.setattr(
        ingestion_cli,
        "run_compute_features",
        lambda symbols: called.append(symbols),
    )

    ingestion_cli.compute_features()
    assert called == [None]


def test_cli_run_daily_execution(monkeypatch):
    """Test full run-daily command invoked via Typer CLI."""
    calls = []

    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_prices",
        lambda since, symbols: calls.append(("prices", since, symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_compute_features",
        lambda symbols: calls.append(("features", symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_news",
        lambda symbols: calls.append(("news", symbols)),
    )
    monkeypatch.setattr(
        ingestion_cli,
        "run_score_sentiment",
        lambda: calls.append(("sentiment",)),
    )

    result = runner.invoke(ingestion_cli.app, ["run-daily", "--since", "2022-01-01", "--symbols", "AAPL,MSFT"])
    assert result.exit_code == 0
    assert calls[0] == ("prices", "2022-01-01", "AAPL,MSFT")
    assert calls[1] == ("features", "AAPL,MSFT")
    assert calls[2] == ("news", "AAPL,MSFT")
    assert calls[3] == ("sentiment",)


def test_cli_ingest_prices_with_default_since(monkeypatch):
    """Test ingest-prices command with defaults."""
    called = []
    monkeypatch.setattr(
        ingestion_cli,
        "run_ingest_prices",
        lambda since, symbols: called.append((since, symbols)),
    )

    result = runner.invoke(ingestion_cli.app, ["ingest-prices"])
    assert result.exit_code == 0
    assert called == [("2020-01-01", None)]
