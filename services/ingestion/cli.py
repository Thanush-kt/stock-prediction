"""Typer CLI for Phase 1 ingestion."""
from __future__ import annotations

import datetime as dt
from typing import Sequence

import typer

from packages.shared.config import get_settings
from packages.shared.db import session_scope
from packages.shared.logging import get_logger
from services.broker import cli as broker_cli
from services.ingestion import features, news, prices, sentiment
from services.model import cli as model_cli
from services.signal import cli as signal_cli

app = typer.Typer(
    add_completion=False,
    help="Stock-Prediction CLI — Phase 1 ingestion + Phase 2 model + Phase 3 signal/broker.",
)
log = get_logger(__name__)
model_cli.register(app)
signal_cli.register(app)
broker_cli.register(app)


def _watchlist() -> list[str]:
    wl = get_settings().watchlist
    if not wl:
        raise typer.BadParameter("WATCHLIST env var is empty.")
    return wl


def parse_symbols(symbols: str | Sequence[str] | None = None) -> list[str]:
    """Normalize symbols parameter into a clean list of uppercase symbol strings.

    If symbols is None or an empty string, falls back to the configured WATCHLIST.
    Safely ignores Typer OptionInfo/ArgumentInfo if passed through direct Python invocation.
    """
    if symbols is None:
        return _watchlist()
    if isinstance(symbols, str):
        cleaned = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        return cleaned if cleaned else _watchlist()
    if isinstance(symbols, (list, tuple, set)):
        cleaned = [str(s).strip().upper() for s in symbols if str(s).strip()]
        return cleaned if cleaned else _watchlist()
    # Fallback if a Typer OptionInfo/ArgumentInfo object is passed at runtime
    return _watchlist()


def run_ingest_prices(
    since: dt.date | str = "2020-01-01",
    symbols: str | Sequence[str] | None = None,
) -> None:
    """Internal core logic for price ingestion."""
    start = dt.date.fromisoformat(since) if isinstance(since, str) else since
    target_symbols = parse_symbols(symbols)
    with session_scope() as session:
        for symbol in target_symbols:
            prices.ingest_symbol(session, symbol, start)


def run_compute_features(
    symbols: str | Sequence[str] | None = None,
) -> None:
    """Internal core logic for feature/indicator computation."""
    target_symbols = parse_symbols(symbols)
    with session_scope() as session:
        for symbol in target_symbols:
            features.compute_for_symbol(session, symbol)


def run_ingest_news(
    symbols: str | Sequence[str] | None = None,
) -> None:
    """Internal core logic for news headline ingestion."""
    target_symbols = parse_symbols(symbols)
    with session_scope() as session:
        for symbol in target_symbols:
            news.ingest_symbol(session, symbol)


def run_score_sentiment() -> None:
    """Internal core logic for unscored sentiment scoring."""
    with session_scope() as session:
        sentiment.score_unscored(session)


def run_daily_pipeline(
    since: dt.date | str = "2020-01-01",
    symbols: str | Sequence[str] | None = None,
) -> None:
    """Internal pipeline executing all four ingestion steps in sequence."""
    run_ingest_prices(since=since, symbols=symbols)
    run_compute_features(symbols=symbols)
    run_ingest_news(symbols=symbols)
    run_score_sentiment()


@app.command("ingest-prices")
def ingest_prices(
    since: str = typer.Option("2020-01-01", help="ISO date — earliest bar to fetch."),
    symbols: str | None = typer.Option(None, help="Comma-separated symbols; defaults to WATCHLIST."),
) -> None:
    raw_symbols = symbols if isinstance(symbols, str) else None
    run_ingest_prices(since=since, symbols=raw_symbols)


@app.command("compute-features")
def compute_features(
    symbols: str | None = typer.Option(None, help="Comma-separated symbols; defaults to WATCHLIST."),
) -> None:
    raw_symbols = symbols if isinstance(symbols, str) else None
    run_compute_features(symbols=raw_symbols)


@app.command("ingest-news")
def ingest_news(
    symbols: str | None = typer.Option(None, help="Comma-separated symbols; defaults to WATCHLIST."),
) -> None:
    raw_symbols = symbols if isinstance(symbols, str) else None
    run_ingest_news(symbols=raw_symbols)


@app.command("score-sentiment")
def score_sentiment() -> None:
    run_score_sentiment()


@app.command("run-daily")
def run_daily(
    since: str = typer.Option("2020-01-01", help="ISO date — earliest bar to fetch."),
    symbols: str | None = typer.Option(None, help="Comma-separated symbols; defaults to WATCHLIST."),
) -> None:
    """Run all four ingestion steps in sequence. Cron entry point."""
    raw_symbols = symbols if isinstance(symbols, str) else None
    run_daily_pipeline(since=since, symbols=raw_symbols)


if __name__ == "__main__":
    app()
