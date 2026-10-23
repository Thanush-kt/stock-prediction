import type {
  EquityPoint,
  MarketData,
  Order,
  Position,
  Prediction,
  PredictionAccuracy,
  PriceBar,
  RiskAnalysis,
  Signal,
  StockPredictionSessions,
  Ticker,
} from '@/types/api';

const BASE =
  typeof window === 'undefined'
    ? `http://${process.env.API_HOST ?? '127.0.0.1'}:${process.env.API_PORT ?? '8000'}`
    : '/api';

async function getAuthToken(): Promise<string | null> {
  if (typeof window === 'undefined') {
    try {
      const { auth } = await import('@clerk/nextjs/server');
      const { getToken } = await auth();
      return await getToken();
    } catch {
      return null;
    }
  } else {
    try {
      const clerk = (window as unknown as {
        Clerk?: { session?: { getToken: () => Promise<string | null> } };
      }).Clerk;
      return (await clerk?.session?.getToken()) ?? null;
    } catch {
      return null;
    }
  }
}

async function getJson<T>(path: string, tokenOverride?: string | null): Promise<T> {
  const token = tokenOverride !== undefined ? tokenOverride : await getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    cache: 'no-store',
    headers,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  stocks: (activeOnly: boolean = true) =>
    getJson<Ticker[]>(`/stocks${activeOnly ? '?active_only=true' : ''}`),

  stockMarketData: (symbol: string) =>
    getJson<MarketData>(`/stocks/${encodeURIComponent(symbol)}/market-data`),

  stockPriceHistory: (symbol: string, days: number = 90) =>
    getJson<PriceBar[]>(`/stocks/${encodeURIComponent(symbol)}/price-history?days=${days}`),

  stockRisk: (symbol: string) =>
    getJson<RiskAnalysis>(`/stocks/${encodeURIComponent(symbol)}/risk`),

  positions: () => getJson<Position[]>('/positions'),

  predictions: (
    params: {
      limit?: number;
      symbol?: string;
      model_version?: string;
      target_session_from?: string;
      target_session_to?: string;
    } = {}
  ) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.symbol) q.set('symbol', params.symbol);
    if (params.model_version) q.set('model_version', params.model_version);
    if (params.target_session_from) q.set('target_session_from', params.target_session_from);
    if (params.target_session_to) q.set('target_session_to', params.target_session_to);
    const qs = q.toString();
    return getJson<Prediction[]>(`/predictions${qs ? `?${qs}` : ''}`);
  },

  predictionsLatest: (params: { symbol?: string; model_version?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.symbol) q.set('symbol', params.symbol);
    if (params.model_version) q.set('model_version', params.model_version);
    const qs = q.toString();
    return getJson<Prediction[]>(`/predictions/latest${qs ? `?${qs}` : ''}`);
  },

  predictionSessions: (params: { symbol?: string; model_version?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.symbol) q.set('symbol', params.symbol);
    if (params.model_version) q.set('model_version', params.model_version);
    const qs = q.toString();
    return getJson<StockPredictionSessions[]>(`/predictions/sessions${qs ? `?${qs}` : ''}`);
  },

  predictionAccuracy: (params: { symbol?: string; model_version?: string; days?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.symbol) q.set('symbol', params.symbol);
    if (params.model_version) q.set('model_version', params.model_version);
    if (params.days) q.set('days', String(params.days));
    const qs = q.toString();
    return getJson<PredictionAccuracy[]>(`/predictions/accuracy${qs ? `?${qs}` : ''}`);
  },

  signals: (
    params: {
      limit?: number;
      decision?: 'BUY' | 'SELL' | 'HOLD' | 'NO_TRADE';
      symbol?: string;
    } = {}
  ) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.decision) q.set('decision', params.decision);
    if (params.symbol) q.set('symbol', params.symbol);
    const qs = q.toString();
    return getJson<Signal[]>(`/signals${qs ? `?${qs}` : ''}`);
  },

  orders: (params: { limit?: number; status?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.status) q.set('status', params.status);
    const qs = q.toString();
    return getJson<Order[]>(`/orders${qs ? `?${qs}` : ''}`);
  },

  equity: (params: { from?: string; to?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.from) q.set('from', params.from);
    if (params.to) q.set('to', params.to);
    const qs = q.toString();
    return getJson<EquityPoint[]>(`/equity${qs ? `?${qs}` : ''}`);
  },
};
