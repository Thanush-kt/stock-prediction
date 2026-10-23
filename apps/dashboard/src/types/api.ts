// Response models mirroring services/api/schemas.py.
// Keep this hand-rolled until/unless we wire openapi-typescript generation.

export interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
  updated_at: string;
  source: string;
}

export interface Signal {
  id: number;
  symbol: string;
  ts: string;
  model_version: string;
  score: number;
  decision: 'BUY' | 'SELL' | 'HOLD' | 'NO_TRADE';
  rationale: Record<string, unknown>;
  created_at: string;
}

export interface Order {
  id: number;
  symbol: string;
  side: string;
  qty: number;
  order_type: string;
  limit_price: number | null;
  stop_price: number | null;
  take_profit: number | null;
  status: string;
  submitted_at: string;
  filled_at: string | null;
  broker_order_id: string | null;
  signal_id: number | null;
}

export interface EquityPoint {
  ts: string;
  equity: number;
  cash: number;
  exposure_pct: number;
  max_drawdown: number;
  n_open_positions: number;
  halted: boolean;
}

export interface Prediction {
  id: number;
  symbol: string;
  ts: string;
  model_version: string;
  score: number;
  label_pred: number;
  target_session?: string | null;
  data_cutoff_ts?: string | null;
  generated_at?: string | null;
  actual_close?: number | null;
  actual_label?: number | null;
  evaluated_at?: string | null;
}

export interface SessionPredictionDetail {
  target_session: string;
  session_label: string;
  is_trading_day: boolean;
  status: 'available' | 'pending_close' | 'stale' | 'unavailable';
  timing?: 'before_session' | 'during_session' | 'future_session' | null;
  prediction?: Prediction | null;
  actual_outcome?: 'correct' | 'incorrect' | 'pending' | null;
  message?: string | null;
}

export interface StockPredictionSessions {
  symbol: string;
  exchange: string;
  exchange_timezone: string;
  is_market_open: boolean;
  current_session_date: string;
  next_session_date: string;
  today: SessionPredictionDetail;
  tomorrow: SessionPredictionDetail;
  latest_quote?: MarketData | null;
}

export interface PredictionAccuracy {
  symbol: string;
  model_version: string;
  n_evaluated: number;
  n_correct: number;
  accuracy: number;
  period_days: number;
}

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
  open: number | null;
  high: number | null;
  low: number | null;
  close_prev: number | null;
  change_pct: number | null;
  source: string;
}

export interface PriceBar {
  symbol: string;
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
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
  as_of: string;
}
