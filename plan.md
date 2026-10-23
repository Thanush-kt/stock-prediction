# Stock-Prediction — Evidence-Based Implementation Plan

> **Planning mode only.** No files have been modified. Awaiting approval before implementation starts.

---

## 1. Executive Summary

The Stock-Prediction project is a **well-structured, phase-based monorepo** that implements a complete algorithmic trading pipeline using Python (FastAPI, SQLAlchemy, XGBoost) and Next.js 16. The backend covers data ingestion, ML training, signal generation, and Alpaca paper trading. The frontend dashboard displays portfolio state and predictions.

**What already works well:**
- Full data ingestion pipeline (yfinance → `price_bars`, `indicators`, `news_items`, `sentiments`)
- XGBoost walk-forward CV with proper leakage prevention
- BUY/SELL/HOLD signal engine with JSON rationale audit trail
- PostgreSQL advisory lock for concurrency safety
- Clerk JWT authentication on both backend and frontend
- 23 test modules covering almost all existing functionality

**What is missing relative to the stated goal:**
1. The **watchlist is hardcoded** to `AAPL,MSFT,NVDA` — no Indian (`.NS`) or multi-exchange support
2. No **stock selector** on the dashboard — no way for a user to pick a stock and see its prediction
3. The `predictions` table has **no `target_session` or `actual_close` columns** — history evaluation is not possible
4. **No risk analysis endpoint** — `historical_volatility`, `ATR`, stop-loss, and position-size calculations are absent from the API
5. **No `GET /stocks` endpoint** — no way to discover supported symbols or search by name
6. **No `GET /stocks/{symbol}/market-data` endpoint** — the dashboard cannot show live prices
7. The **`signals` router does not filter by symbol** — the dashboard cannot show per-stock signals
8. The **predictions page shows historical walk-forward CV rows**, not a live next-session prediction
9. The **`NO TRADE` decision** (rejected at validation) is never surfaced to the UI
10. **No price chart** for individual stocks on the dashboard

---

## 2. Repository Architecture Summary

```
Stock-Prediction/
├── packages/shared/          # config, db, models, logging  [SHARED]
│   ├── config.py             # Pydantic Settings (watchlist, Clerk, Alpaca, DB)
│   ├── db.py                 # SQLAlchemy engine, session, upsert_ignore, advisory lock
│   ├── models.py             # 12 ORM tables (see schema below)
│   └── logging.py
├── services/
│   ├── ingestion/            # Phase 1 — yfinance OHLCV, pandas-ta indicators, news, VADER
│   ├── model/                # Phase 2 — XGBoost WF-CV train/predict/backtest
│   ├── signal/               # Phase 3 — BUY/SELL/HOLD runner + validation
│   ├── broker/               # Phase 3 — Alpaca paper client + reconcile
│   └── api/                  # Phase 3.5 — FastAPI read-only shim (5 routers)
├── apps/dashboard/           # Phase 3.5 — Next.js 16 + Clerk + Recharts
├── migrations/               # 4 Alembic migrations (0001–0004)
├── tests/                    # 23 test files, SQLite-in-memory
├── docker-compose.yml        # Postgres 16 only
└── pyproject.toml            # uv / pip project, Python 3.12
```

**Current DB schema (12 tables across 4 migrations):**

| Table | Purpose | Key columns |
|---|---|---|
| `tickers` | Watchlist master | `symbol`, `name`, `active` |
| `price_bars` | Daily OHLCV | `symbol`, `ts`, OHLCV, `source` |
| `indicators` | Long-form tech indicators | `symbol`, `ts`, `name`, `value` |
| `news_items` | Headlines | `symbol`, `headline`, `url`, `published_at` |
| `sentiments` | VADER scores per news item | `news_item_id`, `compound`, `pos`, `neu`, `neg` |
| `predictions` | XGBoost outputs | `symbol`, `ts`, `model_version`, `score`, `label_pred` |
| `backtest_runs` | Backtest metrics | `model_version`, `sharpe`, `max_drawdown`, `hit_rate` |
| `signals` | BUY/SELL/HOLD decisions | `symbol`, `ts`, `model_version`, `decision`, `rationale` JSON |
| `orders` | Local mirror of Alpaca orders | `symbol`, `side`, `qty`, `status`, `signal_id` |
| `trades` | Fills per order | `order_id`, `qty`, `price` |
| `positions` | Current holdings | `symbol`, `qty`, `avg_price` |
| `risk_state` | Equity/cash/exposure timeseries | `equity`, `cash`, `exposure_pct`, `halted` |

---

## 3. Feature-by-Feature Audit Table

| # | Feature | Status | Source Files | Evidence | Remaining Work |
|---|---|---|---|---|---|
| 1 | **yfinance price ingestion** | ✅ COMPLETE | `services/ingestion/prices.py` | `fetch_ohlcv`, `ingest_symbol` implemented; upsert-on-conflict keyed on `(symbol, ts)` | None |
| 2 | **Technical indicator compute** | ✅ COMPLETE | `services/ingestion/features.py` | 12 indicators via pandas-ta; long-form upsert | None |
| 3 | **News ingestion (NewsAPI)** | ✅ COMPLETE | `services/ingestion/news.py` | Graceful no-op when `NEWSAPI_KEY` missing | None |
| 4 | **VADER sentiment scoring** | ✅ COMPLETE | `services/ingestion/sentiment.py` | Scores unscored news items | None |
| 5 | **Indian stock support** | ❌ INCOMPLETE | `packages/shared/config.py:16` | `watchlist_raw` default is `"AAPL,MSFT,NVDA"`; no `.NS` suffix handling; no BSE/NSE calendar | Add `.NS` tickers to watchlist; plan exchange-aware calendar in validation |
| 6 | **Multi-stock symbol selector** | ❌ INCOMPLETE | None | No `GET /stocks` endpoint; no frontend selector UI | New API router + frontend component |
| 7 | **Ticker validation** | ⚠️ PARTIALLY COMPLETE | `services/ingestion/prices.py:27-29` | Logs warning if yfinance returns empty; no explicit 404 | Add validation wrapper that raises `HTTPException` |
| 8 | **Exchange calendar (NYSE)** | ⚠️ PARTIALLY COMPLETE | `services/signal/validation.py:22-92` | NYSE holiday/trading-day logic exists **only for signal staleness**; not used for ingestion or NSE | Extend to NSE calendar; use in ingestion skip logic |
| 9 | **XGBoost walk-forward CV** | ✅ COMPLETE | `services/model/train.py` | 252/63/63 default windows; leakage check at L158; per-fold predictions persisted | None |
| 10 | **Leakage prevention** | ✅ COMPLETE | `services/model/train.py:156-162` | Hard `RuntimeError` if `max_train_ts >= min_val_ts` | None |
| 11 | **Next-session prediction (live inference)** | ⚠️ PARTIALLY COMPLETE | `services/model/predict.py` | `build_feature_matrix(..., require_target=False)` scores latest bars; writes to `predictions` table | No `target_session` field; API returns all historical predictions, not just the latest one per symbol |
| 12 | **Prediction persistence** | ✅ COMPLETE | `services/model/train.py:_write_predictions`; `services/model/predict.py` | `upsert_ignore` keyed on `(symbol, ts, model_version)` — never overwrites | None |
| 13 | **Prediction history retention** | ⚠️ PARTIALLY COMPLETE | `packages/shared/models.py:117-133` | `predictions` table has `id`, `symbol`, `ts`, `score`, `label_pred`, `model_version` | Missing: `target_session` date, `actual_close`, `data_cutoff_ts`, `evaluated_at` columns |
| 14 | **Actual vs. predicted tracking** | ❌ INCOMPLETE | None | No column for actual outcome; no job that looks up close[t+1] and writes back | New migration + backfill job |
| 15 | **Prediction accuracy over time** | ❌ INCOMPLETE | None | `BacktestRun.hit_rate` exists but is a single aggregate, not per-day per-symbol accuracy | New API endpoint using predictions + price_bars join |
| 16 | **BUY signal** | ✅ COMPLETE | `services/signal/rules.py:109-110` | All gates: bullish score, trend, sentiment, position slot, exposure cap | None |
| 17 | **SELL signal** | ✅ COMPLETE | `services/signal/rules.py:81-83` | Exit on bearish score while already long | None |
| 18 | **HOLD signal** | ✅ COMPLETE | `services/signal/rules.py:85-107` | 6 distinct HOLD reasons in rationale | None |
| 19 | **NO TRADE decision** | ⚠️ PARTIALLY COMPLETE | `services/signal/runner.py:493-504` | Validation failures produce a warning + error in `RunSummary.errors`; **not** persisted as a signal row and **not** surfaced to dashboard | Plan a `NO_TRADE` decision written to signals table |
| 20 | **Signal explanation** | ✅ COMPLETE | `services/signal/rules.py:60-79` | Full `rationale` JSON with every gate's value and pass/fail | None |
| 21 | **Concurrency protection** | ✅ COMPLETE | `packages/shared/db.py:98-155` | PostgreSQL advisory lock `pg_try_advisory_lock`; SQLite thread lock fallback | None |
| 22 | **Order deduplication** | ✅ COMPLETE | `services/signal/runner.py:217-226`; `migrations/0004_order_signal_unique.py` | Unique partial index on `signal_id WHERE signal_id IS NOT NULL`; early-return if order exists | None |
| 23 | **Historical volatility** | ❌ INCOMPLETE | None | `RiskState` stores `max_drawdown` and `exposure_pct` at portfolio level; no per-symbol vol | New computation layer |
| 24 | **ATR / volatility indicator** | ❌ INCOMPLETE | None | ATR is not in `INDICATOR_COLUMNS` in `services/ingestion/features.py` | Add ATR to indicator compute + API response |
| 25 | **Stop-loss / take-profit calc** | ⚠️ PARTIALLY COMPLETE | `services/signal/runner.py:32-34, 238-239` | `STOP_LOSS_PCT = 0.02`, `TAKE_PROFIT_PCT = 0.04` used for orders only; not exposed in API | Expose in a `/stocks/{symbol}/risk` endpoint |
| 26 | **Risk/reward ratio** | ❌ INCOMPLETE | None | Not computed anywhere | New calculation |
| 27 | **Position sizing** | ⚠️ PARTIALLY COMPLETE | `services/signal/runner.py:167-171` | `_qty_for_target` uses `target_pct=5%` of equity; not per-symbol, not exposed to API | Expose per-symbol suggestion in risk endpoint |
| 28 | **Portfolio exposure** | ⚠️ PARTIALLY COMPLETE | `packages/shared/models.py:258` | Stored in `risk_state.exposure_pct`; exposed via `/equity` endpoint | No per-symbol risk API |
| 29 | **Risk categories / labels** | ❌ INCOMPLETE | None | No volatility bucketing (Low/Medium/High risk) | New classification layer |
| 30 | **FastAPI auth (Clerk JWT)** | ✅ COMPLETE | `services/api/deps.py` | Full RS256/ES256/RS384/RS512 verification; JWKS caching; all 5 protected routers | None |
| 31 | **`GET /health`** | ✅ COMPLETE | `services/api/routers/health.py` | Public liveness probe | None |
| 32 | **`GET /positions`** | ✅ COMPLETE | `services/api/routers/positions.py` | Returns non-zero positions | None |
| 33 | **`GET /signals`** | ⚠️ PARTIALLY COMPLETE | `services/api/routers/signals.py` | Filters by `decision`; **missing `symbol` filter** | Add `symbol` query param |
| 34 | **`GET /orders`** | ✅ COMPLETE | `services/api/routers/orders.py` | Filters by `status` | None |
| 35 | **`GET /equity`** | ✅ COMPLETE | `services/api/routers/equity.py` | Time-range filter; returns `risk_state` series | None |
| 36 | **`GET /predictions`** | ⚠️ PARTIALLY COMPLETE | `services/api/routers/predictions.py` | Returns all historical predictions; **missing**: latest-only flag, `target_session`, `actual_outcome` | Extend response schema and add `/predictions/latest` endpoint |
| 37 | **`GET /stocks`** | ❌ INCOMPLETE | None | No endpoint to list supported symbols | New router |
| 38 | **`GET /stocks/{symbol}/market-data`** | ❌ INCOMPLETE | None | No live price endpoint | New router |
| 39 | **`GET /stocks/{symbol}/risk`** | ❌ INCOMPLETE | None | No per-symbol risk analysis API | New router |
| 40 | **Next.js dashboard — Portfolio** | ✅ COMPLETE | `apps/dashboard/src/app/(root)/dashboard/page.tsx` | Shows positions + summary cards from `/positions` and `/equity` | None |
| 41 | **Next.js dashboard — Predictions page** | ⚠️ PARTIALLY COMPLETE | `apps/dashboard/src/app/(root)/predictions/page.tsx` | Shows all historical predictions with filters; **no stock selector; no target session; no actual outcome column** | Extend with stock selector and new columns |
| 42 | **Next.js dashboard — Signals page** | ⚠️ PARTIALLY COMPLETE | `apps/dashboard/src/app/(root)/signals/page.tsx` | Shows signals; **no per-stock filter** | Add symbol filter |
| 43 | **Historical price chart** | ❌ INCOMPLETE | None | `EquityChart` shows portfolio equity; no per-stock OHLCV chart | New `StockPriceChart` component |
| 44 | **Risk analysis panel** | ❌ INCOMPLETE | None | No risk panel component on dashboard | New component |
| 45 | **Stock search / selector** | ❌ INCOMPLETE | None | No combobox or search UI | New `StockSelector` component |
| 46 | **Loading / error / empty states** | ✅ COMPLETE | `apps/dashboard/src/components/ErrorMessage.tsx`; `loading.tsx` | Per-page loading skeletons; error messages | None |
| 47 | **Alpaca paper trading** | ✅ COMPLETE | `services/broker/alpaca.py` | Bracket orders, market orders, retry logic, duplicate detection | None |
| 48 | **Prediction → order separation** | ✅ COMPLETE | Architecture (CLAUDE.md line 55) | `stockpred predict` is separate CLI from `run-signals`; API has no write endpoints | None |
| 49 | **Live trading disabled** | ✅ COMPLETE | `packages/shared/config.py:21-23` | `alpaca_base_url` defaults to `paper-api.alpaca.markets` | None |
| 50 | **Backtest engine** | ✅ COMPLETE | `services/model/backtest.py` | Sharpe, max drawdown, hit rate, total return, turnover | None |

---

## 4. Incomplete / Broken Functionality (Priority List)

| Priority | Item | Impact |
|---|---|---|
| 🔴 P1 | No stock selector UI — user cannot explore a specific stock | Blocks core user journey |
| 🔴 P1 | No `GET /stocks` or `GET /stocks/{symbol}/market-data` API | Blocks selector and price display |
| 🔴 P1 | Indian stock support (`.NS` suffix, NSE calendar) | Core feature requirement |
| 🔴 P1 | `predictions` table missing `target_session`, `data_cutoff_ts`, `actual_close` | Cannot distinguish "today's prediction" from historical |
| 🔴 P1 | No actual-vs-predicted evaluation job | Cannot compute accuracy |
| 🟠 P2 | `GET /signals` missing `symbol` filter | Cannot show signals for selected stock |
| 🟠 P2 | `GET /predictions` missing `latest` semantics | Predictions page is confusing |
| 🟠 P2 | No risk analysis API (`/stocks/{symbol}/risk`) | Missing volatility, ATR, stop-loss display |
| 🟠 P2 | `NO TRADE` not persisted to DB | Missing decision type on dashboard |
| 🟡 P3 | No per-stock price chart component | Poor UX for exploring a stock |
| 🟡 P3 | Risk analysis panel missing from frontend | Feature gap |
| 🟡 P3 | ATR not computed in feature pipeline | Risk calc dependency |
| 🟡 P3 | No frontend tests | CI gap |

---

## 5. Recommended Implementation Architecture

### Principle: Minimal Surgery on Existing Code

The existing architecture is sound. The plan minimizes rewrites:

1. **Extend the DB schema** with two new columns on `predictions` and one new optional table for outcome tracking.
2. **Extend the API** with three new routers and extend two existing routers — all read-only, all protected by Clerk.
3. **Extend the ingestion feature pipeline** to add ATR; no schema change needed (long-form `indicators` table absorbs new names).
4. **Extend the frontend** with a `StockSelector` component, a `StockPriceChart`, and a `RiskPanel` — wired into the existing predictions and signals pages.

### Exchange/Calendar Strategy

- **Indian stocks (NSE):** `yfinance` supports `.NS` suffix natively (e.g. `RELIANCE.NS`). Data flows through the same `price_bars` table unchanged since the schema stores `source = "yfinance"` and `symbol` is a `String(16)` that accommodates `.NS` suffixes.
- **Calendar:** The existing `is_trading_day` / `get_nyse_holidays` logic in `validation.py` is NYSE-specific. For Indian stocks, prediction staleness validation should skip the NYSE calendar and use calendar-day staleness only (NSE holidays are not needed for prediction staleness — we just care that the data was ingested after the last close).
- **Crypto (BTC-USD, ETH-USD) and commodities (GC=F):** yfinance supports these; they trade continuously so "next session" means next UTC day. The model can be trained on them with the same pipeline.
- **Prediction scope:** The XGBoost model is symbol-agnostic. Given enough data (≥252+63 trading days), any symbol can be trained. The model artifact file is named `{model_version}.joblib` — we can train per-symbol models (e.g. `v1_RELIANCE.NS.joblib`) or a pooled model. **Plan: pooled model by default, with per-symbol fallback.**

### Separating Prediction Support from Broker Execution

- **Prediction support:** All tickers in the watchlist can receive predictions — price ingest, feature compute, train, predict.
- **Broker execution (Alpaca):** Alpaca only supports US equities. Indian stocks and crypto will be excluded from order generation (enforced in `services/signal/runner.py` by checking symbol suffix before calling `_submit_order`).

---

## 6. Detailed Phased Implementation Roadmap

---

### Phase 1 — Repository Audit and Architecture Verification ✅ (this document)

**Objective:** Verify the exact state of the codebase against stated requirements.
**Status:** Complete — this plan is the output of Phase 1.

---

### Phase 2 — Market Data and Multi-Stock Support

**Objective:** Extend the watchlist and data pipeline to support Indian, international, crypto, and commodity symbols via yfinance.

**Current state:** `config.py` hardcodes `watchlist_raw = "AAPL,MSFT,NVDA"`. No `.NS` handling.

**Files to modify:**

#### [MODIFY] `packages/shared/config.py`
```diff
-    watchlist_raw: str = Field(default="AAPL,MSFT,NVDA", alias="WATCHLIST")
+    watchlist_raw: str = Field(
+        default="AAPL,MSFT,NVDA,RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,SBIN.NS,GOOGL,NVDA,TSLA,BTC-USD,ETH-USD,GC=F",
+        alias="WATCHLIST",
+    )
```

Add a helper property:
```python
@property
def watchlist_alpaca_eligible(self) -> list[str]:
    """Symbols that can be routed to Alpaca (US equities only)."""
    excluded = {".NS", "-USD", "=F"}
    return [s for s in self.watchlist if not any(s.endswith(e) for e in excluded)]
```

#### [MODIFY] `services/ingestion/prices.py`
- Add `validate_ticker(symbol)` function that calls `yf.Ticker(symbol).fast_info` and raises `ValueError` if the ticker is invalid (returns no `last_price`).
- Add a `timeout` parameter to `fetch_ohlcv` (pass to yfinance via `requests` session).
- Handle yfinance `YFRateLimitError` with exponential backoff (1–4 retries).

#### [MODIFY] `services/signal/runner.py`
```diff
# Before calling _submit_order, skip non-US symbols:
+    _BROKER_INELIGIBLE_SUFFIXES = {".NS", "-USD", "=F"}
+    if any(sym_str.endswith(s) for s in _BROKER_INELIGIBLE_SUFFIXES):
+        log.info("Symbol %s is not Alpaca-eligible; signal generated but no order placed", sym_str)
+        continue
     if decision.decision in ("BUY", "SELL"):
         submitted_qty = _submit_order(...)
```

#### [MODIFY] `services/signal/validation.py`
Add an `exchange_for_symbol(symbol: str) -> str` helper that returns `"NYSE"`, `"NSE"`, `"CRYPTO"`, or `"OTHER"`. Use it to select the correct staleness check (NYSE calendar vs. calendar-day only).

#### [NEW] `services/ingestion/market_data.py`
A thin caching layer over yfinance that:
- Maintains an in-memory LRU cache (256 entries, 5-min TTL) for live quote lookups used by the API.
- Exposes `get_latest_quote(symbol) -> dict` returning `{"price": float, "ts": str, "currency": str}`.
- Raises `SymbolNotFoundError` for invalid symbols.
- Has a 10-second request timeout.

**Database changes:** None — `price_bars` already supports any symbol string.

**New Alembic migration:** None required for this phase.

**Tasks (in order):**
1. Update `config.py` default watchlist and add `watchlist_alpaca_eligible` property.
2. Implement `validate_ticker` in `prices.py`.
3. Implement `market_data.py` caching layer.
4. Add exchange-aware staleness in `validation.py`.
5. Add Alpaca-eligibility gate in `runner.py`.
6. Run `stockpred ingest-prices --since 2023-01-01` for all new symbols (manual step, not automated by plan).

**Test cases:**
- `test_prices.py`: Add test for `.NS` symbol fetching with mocked yfinance.
- `test_prices.py`: Assert `validate_ticker` raises on unknown symbol.
- `test_signal_validation.py`: Test staleness logic bypasses NYSE calendar for `.NS` symbols.

**Acceptance criteria:**
- `stockpred ingest-prices` with `RELIANCE.NS` in watchlist completes without error.
- `validate_ticker("INVALID_XYZ_999")` raises `SymbolNotFoundError`.
- A signal generated for `RELIANCE.NS` produces a `HOLD` row in `signals` but no `Order` row.

**Complexity:** Medium

**Dependencies:** None — Phase 2 is independent.

**Risks:**
- yfinance rate limits (429) for large watchlists — mitigated by retry backoff.
- `.NS` symbols return prices in INR; the backtester treats them as USD-equivalent (acceptable since paper trading is USD-only).
- `String(16)` symbol column is sufficient for `RELIANCE.NS` (11 chars) but NOT for `BTC-USD` (7 chars) — all within limit.

---

### Phase 3 — Prediction Pipeline and Model Validation

**Objective:** Enrich the `Prediction` ORM model with `target_session`, `data_cutoff_ts`, and `generated_at` fields so that "today's prediction" can be unambiguously identified and displayed.

**Current state:**
- `Prediction` has: `id`, `symbol`, `ts` (bar timestamp), `model_version`, `score`, `label_pred`.
- `ts` is the timestamp of the **last bar used as input** — it represents the data cutoff, not the target trading session.
- There is no `target_session` column, so the API cannot answer "what session does this prediction apply to?"

**Files to modify:**

#### [MODIFY] `packages/shared/models.py`
Add three new nullable columns to `Prediction`:
```python
class Prediction(Base):
    # existing columns ...
    target_session: Mapped[dt.date | None] = mapped_column(
        sa.Date, nullable=True,
        comment="The trading session this prediction applies to (next business day after ts)"
    )
    data_cutoff_ts: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Alias of ts — explicit label so clients know what ts means"
    )
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(), nullable=False,
        comment="Wall-clock time when this row was written"
    )
    actual_close: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Filled by the outcome-evaluation job after target_session completes"
    )
    actual_label: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="1 if actual_close > data cutoff close, else 0. Set by evaluation job."
    )
    evaluated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When actual_label was set"
    )
```

> **Note:** All new columns are nullable — this is a **backward-compatible** migration. Existing rows keep NULL for new fields.

#### [NEW] `migrations/versions/0005_prediction_target_session.py`
```python
revision = "0005_prediction_target_session"
down_revision = "0004_order_signal_unique"

def upgrade():
    op.add_column("predictions", sa.Column("target_session", sa.Date(), nullable=True))
    op.add_column("predictions", sa.Column("data_cutoff_ts", sa.DateTime(timezone=True), nullable=True))
    op.add_column("predictions", sa.Column("generated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False))
    op.add_column("predictions", sa.Column("actual_close", sa.Float(), nullable=True))
    op.add_column("predictions", sa.Column("actual_label", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_predictions_target_session", "predictions", ["target_session"])
    op.create_index("ix_predictions_evaluated_at", "predictions", ["evaluated_at"])
```

#### [MODIFY] `services/model/train.py`
Extend `_write_predictions` to populate `target_session` and `data_cutoff_ts`:
```python
from services.signal.validation import is_trading_day
import datetime as dt

def _next_trading_session(ts: dt.datetime) -> dt.date:
    """Return the next trading day after the bar timestamp."""
    d = ts.date() + dt.timedelta(days=1)
    while not is_trading_day(d):
        d += dt.timedelta(days=1)
    return d

# In _write_predictions rows dict:
rows = [{
    "symbol": ...,
    "ts": ...,
    "model_version": ...,
    "score": ...,
    "label_pred": ...,
    "target_session": _next_trading_session(r.ts),
    "data_cutoff_ts": r.ts,
}]
```

#### [MODIFY] `services/model/predict.py`
Same extension: populate `target_session` and `data_cutoff_ts` when upserting live-inference rows.

#### [NEW] `services/model/evaluate.py`
An outcome-evaluation job that:
1. Queries `predictions` where `target_session <= today` AND `actual_close IS NULL`.
2. For each such row, looks up `price_bars` for `(symbol, ts = target_session)`.
3. If found, computes `actual_label = 1 if actual_close > data_cutoff_close else 0` and writes back.
4. Scheduled as a nightly CLI command: `stockpred evaluate-outcomes`.

**Tasks (in order):**
1. Write migration `0005_prediction_target_session.py`.
2. Update `Prediction` ORM model with new columns.
3. Extend `_write_predictions` in `train.py` and `predict.py`.
4. Implement `evaluate.py` and register `stockpred evaluate-outcomes` CLI command.
5. Apply migration (approval step, not in this plan).

**Test cases:**
- `test_model_train.py`: Assert new predictions have non-null `target_session` and `generated_at`.
- New `test_model_evaluate.py`: Insert prediction with `target_session` in the past; insert matching `price_bar`; run evaluate; assert `actual_label` is set.

**Acceptance criteria:**
- After `stockpred predict`, all new prediction rows have `target_session` set.
- After `stockpred evaluate-outcomes`, rows with past `target_session` have `actual_label` populated.
- Existing rows without `target_session` continue to work (nullable, no error).

**Complexity:** Medium

**Dependencies:** Phase 2 (exchange-aware `_next_trading_session` for non-NYSE symbols).

---

### Phase 4 — Prediction Persistence and Historical Evaluation

**Objective:** Expose prediction history, today's prediction, and accuracy metrics through the API.

**Files to modify:**

#### [MODIFY] `services/api/schemas.py`
Extend `PredictionOut`:
```python
class PredictionOut(_ApiModel):
    id: int
    symbol: str
    ts: dt.datetime          # data cutoff bar timestamp
    model_version: str
    score: float
    label_pred: int
    target_session: dt.date | None = None
    data_cutoff_ts: dt.datetime | None = None
    generated_at: dt.datetime | None = None
    actual_close: float | None = None
    actual_label: int | None = None
    evaluated_at: dt.datetime | None = None

class PredictionAccuracyOut(BaseModel):
    symbol: str
    model_version: str
    n_evaluated: int
    n_correct: int
    accuracy: float
    period_days: int
```

#### [MODIFY] `services/api/routers/predictions.py`
Add two new endpoints:

1. **`GET /predictions/latest`** — returns one row per (symbol, model_version) — the most recent prediction:
```python
@router.get("/predictions/latest", response_model=list[PredictionOut])
def latest_predictions(
    symbol: str | None = None,
    model_version: str | None = None,
    session: Session = Depends(get_session),
) -> list[PredictionOut]:
    # Subquery: SELECT symbol, model_version, MAX(ts) as max_ts FROM predictions GROUP BY ...
    # Then join back to get full rows
```

2. **`GET /predictions/accuracy`** — aggregated accuracy:
```python
@router.get("/predictions/accuracy", response_model=list[PredictionAccuracyOut])
def prediction_accuracy(
    symbol: str | None = None,
    model_version: str | None = None,
    days: int = Query(90, ge=7, le=365),
    session: Session = Depends(get_session),
) -> list[PredictionAccuracyOut]:
    # WHERE actual_label IS NOT NULL AND target_session >= today - days
    # GROUP BY symbol, model_version
```

**Existing `GET /predictions`** — add `target_session_from` / `target_session_to` date filters.

**Tasks (in order):**
1. Extend `PredictionOut` and add `PredictionAccuracyOut` to `schemas.py`.
2. Implement `GET /predictions/latest`.
3. Implement `GET /predictions/accuracy`.
4. Extend `GET /predictions` with new filters.

**Test cases:**
- `test_api_predictions.py`: Assert `/predictions/latest` returns one row per symbol.
- `test_api_predictions.py`: Assert `/predictions/accuracy` returns 0.0 when no evaluations exist.
- `test_api_predictions.py`: Assert `/predictions/accuracy` returns correct hit rate after inserting evaluated rows.

**Acceptance criteria:**
- `/predictions/latest?symbol=AAPL` returns exactly one row with `target_session` set.
- `/predictions/accuracy?symbol=AAPL&days=90` returns `n_evaluated`, `n_correct`, `accuracy`.

**Complexity:** Low–Medium

**Dependencies:** Phase 3 (new DB columns).

---

### Phase 5 — Buy/Sell/Hold Signals and Risk Analysis

**Objective:** Add symbol filter to `/signals`, surface `NO_TRADE`, and implement the risk analysis API.

**Files to modify:**

#### [MODIFY] `services/api/routers/signals.py`
Add `symbol` query parameter:
```python
@router.get("/signals", response_model=list[SignalOut])
def list_signals(
    limit: int = Query(50, ge=1, le=500),
    decision: Literal["BUY", "SELL", "HOLD", "NO_TRADE"] | None = None,
    symbol: str | None = None,          # ← new
    session: Session = Depends(get_session),
) -> list[SignalOut]:
```

#### [MODIFY] `services/api/schemas.py`
Add `SignalDecision` to the type annotation (include `"NO_TRADE"`):
```python
class SignalOut(_ApiModel):
    ...
    decision: str  # "BUY" | "SELL" | "HOLD" | "NO_TRADE"
```

#### [NEW] `services/api/routers/stocks.py`
Three new endpoints:

**`GET /stocks`** — list supported symbols from `tickers` table:
```python
class TickerOut(_ApiModel):
    symbol: str
    name: str | None
    exchange: str          # derived from suffix
    asset_class: str       # "equity" | "crypto" | "commodity"
    active: bool

@router.get("/stocks", response_model=list[TickerOut])
def list_stocks(session: Session = Depends(get_session)):
    rows = session.execute(select(Ticker).where(Ticker.active == True).order_by(Ticker.symbol)).scalars().all()
    return [_enrich_ticker(r) for r in rows]
```

**`GET /stocks/{symbol}/market-data`** — live price from cache, or latest DB bar:
```python
class MarketDataOut(BaseModel):
    symbol: str
    price: float
    currency: str
    ts: dt.datetime
    open: float | None
    high: float | None
    low: float | None
    close_prev: float | None
    change_pct: float | None
    source: str   # "live" | "db"

@router.get("/stocks/{symbol}/market-data", response_model=MarketDataOut)
def market_data(symbol: str, session: Session = Depends(get_session)):
    symbol = symbol.upper()
    # Try cache first (services/ingestion/market_data.py)
    # Fall back to latest price_bar row
```

**`GET /stocks/{symbol}/risk`** — per-symbol risk metrics:
```python
class RiskAnalysisOut(BaseModel):
    symbol: str
    hist_volatility_20d: float | None
    hist_volatility_60d: float | None
    atr_14: float | None
    max_drawdown_1y: float | None
    stop_loss_pct: float
    take_profit_pct: float
    risk_reward_ratio: float
    suggested_position_pct: float
    risk_category: str   # "LOW" | "MEDIUM" | "HIGH" | "VERY HIGH"
    risk_explanation: str
    as_of: dt.datetime

@router.get("/stocks/{symbol}/risk", response_model=RiskAnalysisOut)
def risk_analysis(symbol: str, session: Session = Depends(get_session)):
    # Compute from price_bars and indicators tables
    # hist_volatility = std(log_returns) * sqrt(252)
    # atr from indicators table if ATR was computed (see Phase 2 ATR addition)
    # max_drawdown from price_bars
    # stop_loss_pct = STOP_LOSS_PCT constant from runner.py (0.02)
    # take_profit_pct = TAKE_PROFIT_PCT (0.04)
    # risk_reward_ratio = take_profit / stop_loss
    # suggested_position_pct from _qty_for_target logic
```

#### [MODIFY] `services/api/main.py`
Register new router:
```python
from services.api.routers import stocks
application.include_router(stocks.router, tags=["stocks"], dependencies=[Depends(get_current_user)])
```

#### [MODIFY] `services/ingestion/features.py`
Add ATR to `INDICATOR_COLUMNS`:
```python
"ATRr_14": "atr_14",   # pandas-ta ATR, 14-period
```
Add to `compute_indicators`:
```python
out.ta.atr(length=14, append=True)
```

> **Schema note:** The `indicators` table uses long-form storage; adding ATR is a code-only change. No migration required.

**Tasks (in order):**
1. Add ATR to `features.py` indicator pipeline.
2. Add `symbol` filter to `/signals` router.
3. Implement `stocks.py` router with all three endpoints.
4. Register new router in `main.py`.
5. Add new schemas to `schemas.py`.

**Test cases:**
- `test_api_signals.py`: Assert `/signals?symbol=AAPL` returns only AAPL signals.
- New `test_api_stocks.py`:
  - `/stocks` returns all active tickers.
  - `/stocks/AAPL/market-data` returns a `price` field.
  - `/stocks/INVALID/market-data` returns 404.
  - `/stocks/AAPL/risk` returns `hist_volatility_20d` and `atr_14` (or null if no data).
- `test_features.py`: Assert ATR is computed and written to `indicators`.

**Acceptance criteria:**
- `/stocks` returns at least 3 symbols after ingestion.
- `/stocks/AAPL/risk` returns a `risk_category` of "LOW", "MEDIUM", "HIGH", or "VERY HIGH".
- `/stocks/RELIANCE.NS/market-data` returns price in INR (or DB fallback).

**Complexity:** High

**Dependencies:** Phase 2 (ATR data in DB); Phase 3 (prediction metadata for risk context).

---

### Phase 6 — FastAPI Integration and Authentication Verification

**Objective:** Verify all new and existing endpoints are correctly protected; run the full API test suite against the extended schema.

**Files to modify:**

#### [MODIFY] `tests/test_api_auth.py`
Add tests for:
- `/stocks` returns 401 without token.
- `/stocks/AAPL/risk` returns 401 without token.
- `/predictions/latest` returns 401 without token.

#### [MODIFY] `tests/test_api_predictions.py`
Add tests for `/predictions/latest` and `/predictions/accuracy`.

#### [NEW] `tests/test_api_stocks.py`
Full coverage of the new stocks router.

#### [MODIFY] `services/api/main.py`
Verify CORS still allows only `localhost:3000`. Consider making allowed origins configurable via `Settings`.

**Tasks (in order):**
1. Run existing test suite — verify zero regressions.
2. Write new API tests for all new endpoints.
3. Add auth tests for new routes.
4. Smoke-test with `httpx` against a running dev server (manual).

**Acceptance criteria:**
- `pytest -q` passes with zero failures.
- All new endpoints return 401 when called without a valid Clerk token.
- All new endpoints return correct data when called with a valid token in tests.

**Complexity:** Low

**Dependencies:** Phases 3, 4, 5.

---

### Phase 7 — Next.js Dashboard Integration

**Objective:** Add stock selector, per-stock prediction panel, risk analysis panel, price chart, and enhanced predictions table to the dashboard.

**Current state:**
- The dashboard has 5 pages: Portfolio, Predictions, Signals, Orders, Equity Curve.
- No stock selector anywhere.
- `api.ts` has 5 fetch functions matching the 5 existing endpoints.

**Files to modify:**

#### [MODIFY] `apps/dashboard/src/lib/api.ts`
Add new API functions:
```typescript
stocks: () => getJson<Ticker[]>('/stocks'),
stockMarketData: (symbol: string) => getJson<MarketData>(`/stocks/${encodeURIComponent(symbol)}/market-data`),
stockRisk: (symbol: string) => getJson<RiskAnalysis>(`/stocks/${encodeURIComponent(symbol)}/risk`),
predictionsLatest: (params: { symbol?: string; model_version?: string } = {}) =>
  getJson<Prediction[]>('/predictions/latest' + (params.symbol ? `?symbol=${params.symbol}` : '')),
predictionAccuracy: (params: { symbol?: string; days?: number } = {}) =>
  getJson<PredictionAccuracy[]>('/predictions/accuracy'),
```

#### [MODIFY] `apps/dashboard/src/types/api.ts`
Add:
```typescript
export interface Ticker {
  symbol: string;
  name: string | null;
  exchange: string;
  asset_class: string;
  active: boolean;
}

export interface MarketData {
  symbol: string;
  price: number;
  currency: string;
  ts: string;
  change_pct: number | null;
  source: string;
}

export interface RiskAnalysis {
  symbol: string;
  hist_volatility_20d: number | null;
  hist_volatility_60d: number | null;
  atr_14: number | null;
  max_drawdown_1y: number | null;
  stop_loss_pct: number;
  take_profit_pct: number;
  risk_reward_ratio: number;
  suggested_position_pct: number;
  risk_category: 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY HIGH';
  risk_explanation: string;
}

export interface PredictionAccuracy {
  symbol: string;
  model_version: string;
  n_evaluated: number;
  n_correct: number;
  accuracy: number;
  period_days: number;
}

// Extend existing Prediction type:
export interface Prediction {
  id: number;
  symbol: string;
  ts: string;
  model_version: string;
  score: number;
  label_pred: number;
  target_session: string | null;   // ← new
  actual_label: number | null;     // ← new
  generated_at: string | null;    // ← new
}
```

#### [NEW] `apps/dashboard/src/components/StockSelector.tsx`
A searchable combobox that:
- Fetches `/stocks` on mount.
- Filters by search input (client-side filtering from loaded list).
- Groups by exchange (Indian / US Equity / Crypto / Commodity).
- Calls `onSelect(symbol: string)` callback.
- Shows a "No results" state.

```tsx
'use client';
interface StockSelectorProps {
  onSelect: (symbol: string) => void;
  selectedSymbol: string | null;
}
```

#### [NEW] `apps/dashboard/src/components/StockPriceChart.tsx`
A Recharts `CandlestickChart` (or simplified `AreaChart` using close prices) showing 30/90/365 day OHLCV for a selected symbol. Fetches from `/stocks/{symbol}/market-data` for current price and from `/stocks/{symbol}/price-history` (if we add that) or displays from the `predictions` history.

> **Pragmatic alternative:** Use the existing `price_bars` data via a new `GET /stocks/{symbol}/price-history?days=90` endpoint rather than a full candlestick chart. Use Recharts `AreaChart` like the existing `EquityChart`.

#### [NEW] `apps/dashboard/src/components/RiskPanel.tsx`
Displays the output of `/stocks/{symbol}/risk`:
- Volatility gauge (20d, 60d)
- ATR value
- Stop-loss / take-profit levels
- Risk/reward ratio
- Suggested position size
- Risk category badge (color-coded: LOW=green, MEDIUM=amber, HIGH=orange, VERY HIGH=red)

#### [NEW] `apps/dashboard/src/components/PredictionCard.tsx`
Displays the latest prediction for a selected symbol:
- Last close price + timestamp
- Predicted direction (↑ UP / ↓ DOWN) with confidence score
- Target session date
- Model version
- Data cutoff timestamp
- Actual outcome (if evaluated)

#### [MODIFY] `apps/dashboard/src/app/(root)/predictions/page.tsx`
Add the `StockSelector` at the top. When a symbol is selected:
1. Fetch `/predictions/latest?symbol={symbol}` → show `PredictionCard`.
2. Fetch `/predictions?symbol={symbol}` → show history table.
3. Fetch `/predictions/accuracy?symbol={symbol}` → show accuracy metrics.

#### [MODIFY] `apps/dashboard/src/app/(root)/signals/page.tsx`
Add symbol filter. When symbol selected, pass `symbol` query param to `/signals`.

#### [NEW] `apps/dashboard/src/app/(root)/stocks/[symbol]/page.tsx`
A stock detail page combining:
- `PredictionCard`
- `StockPriceChart`
- `RiskPanel`
- `SignalsTable` (filtered to symbol)
- `PredictionsTable` (filtered to symbol, with actual vs. predicted column)

**Navigation update — `DashboardNav.tsx`:**
Add a "Stocks" nav item pointing to `/stocks` (a new stocks listing page).

**Tasks (in order):**
1. Update `api.ts` with new fetch functions.
2. Update `types/api.ts` with new interfaces.
3. Build `StockSelector` component.
4. Build `PredictionCard` component.
5. Build `RiskPanel` component.
6. Build `StockPriceChart` component (Recharts AreaChart with price_bars data).
7. Update `predictions/page.tsx` to use selector + new components.
8. Update `signals/page.tsx` with symbol filter.
9. Add stock detail page `/stocks/[symbol]/page.tsx`.
10. Update `DashboardNav.tsx` with new nav item.

**Acceptance criteria:**
- Selecting `RELIANCE.NS` from the stock selector shows its prediction, risk, and chart.
- The predictions table shows an "Actual" column that is populated for past sessions.
- Selecting `AAPL` shows BUY/SELL/HOLD signals specific to AAPL.
- All loading states show skeleton UI, not blank screens.
- Error states show the `ErrorMessage` component.

**Complexity:** High

**Dependencies:** Phases 4, 5 (new API endpoints).

---

### Phase 8 — Testing, Security, and Regression Checks

**Objective:** Ensure zero regressions; add missing test coverage; verify security controls.

#### New test files:
| File | Coverage |
|---|---|
| `tests/test_api_stocks.py` | `/stocks`, `/stocks/{s}/market-data`, `/stocks/{s}/risk` |
| `tests/test_model_evaluate.py` | `evaluate.py` outcome job |
| `tests/test_ingestion_market_data.py` | Cache, timeout, invalid symbol |

#### Existing tests to extend:
| File | What to add |
|---|---|
| `tests/test_api_auth.py` | Auth on new endpoints |
| `tests/test_api_predictions.py` | `/predictions/latest`, `/predictions/accuracy` |
| `tests/test_api_signals.py` | `?symbol=` filter |
| `tests/test_prices.py` | `.NS` fetch (mocked), invalid symbol |
| `tests/test_signal_validation.py` | Non-NYSE exchange staleness bypass |
| `tests/test_model_train.py` | Assert `target_session` is set |

**Mock strategy (mocked external services):**
- `yfinance`: Use `responses` library or `unittest.mock.patch("yfinance.Ticker")`.
- `NewsAPI`: Already mocked via `responses` in `test_news.py`.
- `Alpaca`: Already mocked via `responses` in `test_broker_alpaca.py`.
- Clerk JWKS: Already mocked in `test_api_auth.py`.

**Acceptance criteria:**
- `pytest -q` with zero failures and ≥85% coverage on new code.
- All new endpoints return 401 without token.
- `validate_ticker("INVALID")` raises without hitting real network.

**Complexity:** Medium

**Dependencies:** Phases 2–7.

---

### Phase 9 — End-to-End Verification and Demonstration Preparation

**Objective:** Manual end-to-end smoke test; prepare a working demonstration.

**Verification checklist (manual):**
- [ ] `docker compose up -d postgres` → Postgres healthy
- [ ] `alembic upgrade head` → all 5 migrations applied without error
- [ ] `stockpred ingest-prices --since 2023-01-01` → AAPL, RELIANCE.NS, BTC-USD ingested
- [ ] `stockpred compute-features` → ATR and existing indicators computed
- [ ] `stockpred train --model-version v1` → model artifact saved to `models/v1.joblib`
- [ ] `stockpred predict --model-version v1` → predictions with `target_session` populated
- [ ] `stockpred run-signals --model-version v1 --dry-run` → signals generated, no orders for `.NS`
- [ ] `stockpred evaluate-outcomes` → past predictions have `actual_label` set
- [ ] `uvicorn services.api.main:app` → API starts on `:8000`
- [ ] `GET /health` → `{"status": "ok"}`
- [ ] `GET /stocks` (with Clerk token) → list including `RELIANCE.NS`
- [ ] `GET /stocks/AAPL/market-data` → price and timestamp
- [ ] `GET /stocks/AAPL/risk` → volatility, ATR, risk category
- [ ] `GET /predictions/latest?symbol=AAPL` → single prediction with `target_session`
- [ ] `GET /predictions/accuracy?symbol=AAPL` → accuracy metrics
- [ ] `nx serve dashboard` → dashboard on `:3000`
- [ ] Stock selector shows all symbols grouped by exchange
- [ ] Selecting `RELIANCE.NS` loads prediction card, risk panel, price chart
- [ ] Predictions table shows "Actual" column with outcomes for past sessions

---

## 7. File-by-File Change Plan

| Phase | File | Action | Description |
|---|---|---|---|
| 2 | `packages/shared/config.py` | MODIFY | Expand default watchlist; add `watchlist_alpaca_eligible` |
| 2 | `services/ingestion/prices.py` | MODIFY | Add `validate_ticker`, retry backoff, timeout |
| 2 | `services/ingestion/market_data.py` | NEW | LRU cache for live quotes |
| 2 | `services/signal/runner.py` | MODIFY | Alpaca-eligibility gate for non-US symbols |
| 2 | `services/signal/validation.py` | MODIFY | Exchange-aware staleness logic |
| 2 | `services/ingestion/features.py` | MODIFY | Add ATR to indicator pipeline |
| 3 | `packages/shared/models.py` | MODIFY | Add 6 new nullable columns to `Prediction` |
| 3 | `migrations/versions/0005_prediction_target_session.py` | NEW | Backward-compatible migration |
| 3 | `services/model/train.py` | MODIFY | Populate `target_session`, `data_cutoff_ts` |
| 3 | `services/model/predict.py` | MODIFY | Same |
| 3 | `services/model/evaluate.py` | NEW | Outcome evaluation job |
| 3 | `services/ingestion/cli.py` | MODIFY | Register `evaluate-outcomes` CLI command |
| 4 | `services/api/schemas.py` | MODIFY | Extend `PredictionOut`; add `PredictionAccuracyOut` |
| 4 | `services/api/routers/predictions.py` | MODIFY | Add `/predictions/latest` and `/predictions/accuracy` |
| 5 | `services/api/routers/signals.py` | MODIFY | Add `symbol` query param |
| 5 | `services/api/routers/stocks.py` | NEW | `/stocks`, `/stocks/{s}/market-data`, `/stocks/{s}/risk` |
| 5 | `services/api/main.py` | MODIFY | Register stocks router |
| 5 | `services/api/schemas.py` | MODIFY | Add `TickerOut`, `MarketDataOut`, `RiskAnalysisOut` |
| 7 | `apps/dashboard/src/lib/api.ts` | MODIFY | Add 5 new fetch functions |
| 7 | `apps/dashboard/src/types/api.ts` | MODIFY | Add `Ticker`, `MarketData`, `RiskAnalysis`, `PredictionAccuracy` types; extend `Prediction` |
| 7 | `apps/dashboard/src/components/StockSelector.tsx` | NEW | Searchable stock combobox |
| 7 | `apps/dashboard/src/components/PredictionCard.tsx` | NEW | Latest prediction display |
| 7 | `apps/dashboard/src/components/RiskPanel.tsx` | NEW | Risk metrics display |
| 7 | `apps/dashboard/src/components/StockPriceChart.tsx` | NEW | Recharts area chart for stock prices |
| 7 | `apps/dashboard/src/app/(root)/predictions/page.tsx` | MODIFY | Add stock selector, new components |
| 7 | `apps/dashboard/src/app/(root)/signals/page.tsx` | MODIFY | Add symbol filter |
| 7 | `apps/dashboard/src/app/(root)/stocks/[symbol]/page.tsx` | NEW | Stock detail page |
| 7 | `apps/dashboard/src/components/DashboardNav.tsx` | MODIFY | Add Stocks nav item |
| 8 | `tests/test_api_stocks.py` | NEW | Full coverage of stocks router |
| 8 | `tests/test_model_evaluate.py` | NEW | Outcome evaluation job tests |
| 8 | `tests/test_ingestion_market_data.py` | NEW | Market data cache tests |
| 8 | `tests/test_api_auth.py` | MODIFY | Auth on new endpoints |
| 8 | `tests/test_api_predictions.py` | MODIFY | New prediction endpoints |
| 8 | `tests/test_api_signals.py` | MODIFY | Symbol filter |

---

## 8. Database Migration Plan

**Migration: `0005_prediction_target_session`**

- **Type:** Backward-compatible additive migration (nullable columns + indices).
- **Risk:** Low — does not alter existing columns or constraints.
- **Rollback:** `alembic downgrade 0004_order_signal_unique` drops the 6 columns and 2 indices.
- **Backfill:** Not planned automatically. Existing rows will have `target_session = NULL`. The `evaluate.py` job will only process rows where `target_session IS NOT NULL` (new rows only).

**No other migrations are required.** All other changes (ATR indicator, new API endpoints, frontend) require no DB schema changes because:
- ATR uses the existing long-form `indicators` table.
- New API endpoints read from existing tables.
- The `tickers` table already contains all needed fields for the `/stocks` endpoint.

---

## 9. API and Frontend Integration Plan

### New API Surface (all protected by Clerk JWT)

```
GET /stocks                           → list[TickerOut]
GET /stocks/{symbol}/market-data      → MarketDataOut
GET /stocks/{symbol}/risk             → RiskAnalysisOut
GET /predictions/latest               → list[PredictionOut]  (one per symbol+model)
GET /predictions/accuracy             → list[PredictionAccuracyOut]
GET /predictions?target_session_from= → list[PredictionOut]  (extended filters)
GET /signals?symbol=                  → list[SignalOut]       (extended filter)
```

### Frontend → API Dependency Map

| Frontend Component | API Endpoint(s) |
|---|---|
| `StockSelector` | `GET /stocks` |
| `PredictionCard` | `GET /predictions/latest?symbol={s}` |
| `RiskPanel` | `GET /stocks/{s}/risk` |
| `StockPriceChart` | `GET /stocks/{s}/market-data` + `price_bars` via new endpoint |
| `PredictionsTable` (history) | `GET /predictions?symbol={s}` |
| Accuracy section | `GET /predictions/accuracy?symbol={s}` |
| Signals (filtered) | `GET /signals?symbol={s}` |

### Data Flow (End-to-End for a User)

```
User opens dashboard
  → Selects "RELIANCE.NS" from StockSelector
  → Parallel fetches:
      GET /stocks/RELIANCE.NS/market-data  → current price (₹ from yfinance cache or DB)
      GET /predictions/latest?symbol=RELIANCE.NS → PredictionCard data
      GET /stocks/RELIANCE.NS/risk         → RiskPanel data
      GET /predictions?symbol=RELIANCE.NS&limit=30 → history table
      GET /predictions/accuracy?symbol=RELIANCE.NS → accuracy banner
      GET /signals?symbol=RELIANCE.NS&limit=20     → signals section
```

---

## 10. Testing Strategy and Acceptance Criteria

### Automated Tests

```bash
# Full suite (must pass before any PR merges)
pytest -q

# Specific new test modules
pytest tests/test_api_stocks.py -v
pytest tests/test_model_evaluate.py -v
pytest tests/test_ingestion_market_data.py -v

# Existing regression check
pytest tests/test_signal_runner.py tests/test_broker_reconcile.py tests/test_postgres_concurrency.py -v
```

### Test Coverage Requirements
- All new service modules: ≥90% line coverage.
- All new API routers: 100% endpoint coverage (happy path + 401 + 404).
- No external network calls in any test (use `responses` or `unittest.mock.patch`).

### Manual Verification Steps (post-Phase 9)
1. Confirm Indian stock data (e.g. RELIANCE.NS) appears in the stock selector.
2. Confirm a RELIANCE.NS signal is generated but no Alpaca order is placed.
3. Confirm the predictions page shows a `target_session` date in the future.
4. Confirm `actual_label` is populated after running `evaluate-outcomes` for past sessions.
5. Confirm the risk panel shows a meaningful `risk_category` for at least one stock.

---

## 11. Dependencies and Blockers

| Dependency | Required By | Notes |
|---|---|---|
| yfinance >= 0.2.40 | Phase 2 | Already in `pyproject.toml` |
| `pandas-ta` ATR | Phase 5 | Already installed; just needs to be called |
| Clerk keys in `.env` | Phases 6+ | Already configured |
| PostgreSQL running | Phases 3+ migration | `docker compose up -d postgres` |
| Model artifact `models/v1.joblib` | Phase 9 demo | Must run `stockpred train` and `stockpred predict` |
| NewsAPI key (optional) | Phase 2 | Graceful no-op if missing — not a blocker |

**Blockers (must be resolved before implementation):**
- [ ] User approval of this plan
- [ ] Confirm default watchlist is correct (or provide a custom one in `.env`)
- [ ] Confirm whether pooled model (one model for all symbols) or per-symbol model is preferred

---

## 12. Recommended First Implementation Task

**Start with Phase 3 (migration `0005`)** — it is the most impactful, lowest-risk change:

1. Write `0005_prediction_target_session.py`.
2. Update `Prediction` ORM model.
3. Update `train.py` and `predict.py` to populate `target_session`.
4. Apply migration: `alembic upgrade head`.
5. Re-run `stockpred predict` to populate new rows.

This unblocks Phases 4 and 7 and requires no frontend changes yet. It also demonstrates the "today's prediction" feature immediately.

---

## 13. Phase Completion Checklist

```
Phase 1 — Audit and Architecture
  [x] Repository inspected and findings documented
  [x] Audit table completed with evidence
  [x] Implementation plan created

Phase 2 — Market Data and Multi-Stock Support
  [ ] Config watchlist expanded
  [ ] `validate_ticker` implemented
  [ ] `market_data.py` caching layer created
  [ ] ATR added to indicator pipeline
  [ ] Alpaca-eligibility gate in runner
  [ ] Exchange-aware staleness in validation
  [ ] New symbol data ingested (manual)
  [ ] Tests passing

Phase 3 — Prediction Pipeline and Model Validation
  [ ] Migration 0005 written
  [ ] `Prediction` model extended (6 new nullable columns)
  [ ] `train.py` populates `target_session`
  [ ] `predict.py` populates `target_session`
  [ ] `evaluate.py` job implemented
  [ ] CLI command registered
  [ ] Tests passing

Phase 4 — Prediction Persistence and Historical Evaluation
  [ ] `PredictionOut` extended
  [ ] `PredictionAccuracyOut` added
  [ ] `GET /predictions/latest` implemented
  [ ] `GET /predictions/accuracy` implemented
  [ ] `GET /predictions` date filters added
  [ ] Tests passing

Phase 5 — Signals and Risk Analysis
  [ ] `GET /signals` symbol filter added
  [ ] `GET /stocks` implemented
  [ ] `GET /stocks/{symbol}/market-data` implemented
  [ ] `GET /stocks/{symbol}/risk` implemented
  [ ] Stocks router registered in main.py
  [ ] Tests passing

Phase 6 — Auth Verification
  [ ] All new endpoints tested for 401
  [ ] Full `pytest -q` green

Phase 7 — Frontend Dashboard
  [ ] `api.ts` updated
  [ ] `types/api.ts` updated
  [ ] `StockSelector` built
  [ ] `PredictionCard` built
  [ ] `RiskPanel` built
  [ ] `StockPriceChart` built
  [ ] `predictions/page.tsx` updated
  [ ] `signals/page.tsx` updated
  [ ] Stock detail page created
  [ ] Nav updated

Phase 8 — Testing and Security
  [ ] `test_api_stocks.py` written
  [ ] `test_model_evaluate.py` written
  [ ] `test_ingestion_market_data.py` written
  [ ] All existing tests still pass
  [ ] ≥85% coverage on new code

Phase 9 — End-to-End Verification
  [ ] All manual verification steps in §9 completed
  [ ] Stock selector working for Indian + international stocks
  [ ] Prediction card shows `target_session`
  [ ] Risk panel shows volatility + ATR
  [ ] Accuracy metrics updating after `evaluate-outcomes`
```

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Model strategy:** Should we train a single pooled XGBoost model across all symbols, or a separate model per symbol? The current code trains one model over all symbols in the watchlist. With Indian `.NS` stocks added, the pooled model may lose accuracy for each individual exchange. **Recommendation:** Start pooled (no code change required); plan per-symbol training as a later enhancement.

> [!IMPORTANT]
> **Q2 — Default watchlist:** The plan proposes extending the default watchlist to include Indian stocks and crypto. Should this be the hardcoded default, or should only the `.env` file be updated? **Recommendation:** Update `.env.example` only; leave the default in `config.py` as-is so existing users are not affected.

> [!WARNING]
> **Q3 — Price chart data source:** Should the per-stock price chart fetch historical bars from the existing `price_bars` DB table (requires a new API endpoint `GET /stocks/{symbol}/price-history`) or call yfinance directly from the Next.js frontend (simpler but leaks the data dependency)? **Recommendation:** Add a lightweight `GET /stocks/{symbol}/price-history?days=90` endpoint backed by `price_bars` to keep the API as the single source of truth.

> [!NOTE]
> **Q4 — NO_TRADE persistence:** Currently, validation-rejected symbols are logged but never written to `signals`. Should `NO_TRADE` be persisted as a signal row (requires adding `"NO_TRADE"` to the `decision` column constraint) or kept as a log-only event? Persisting it improves auditability but requires a migration to update the `String(8)` column size (currently just enough for `"SELL"`).
