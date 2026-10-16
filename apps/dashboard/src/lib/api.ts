import type { EquityPoint, Order, Position, Prediction, Signal } from '@/types/api';

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
  positions: () => getJson<Position[]>('/positions'),
  predictions: (params: { limit?: number; symbol?: string; model_version?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.symbol) q.set('symbol', params.symbol);
    if (params.model_version) q.set('model_version', params.model_version);
    const qs = q.toString();
    return getJson<Prediction[]>(`/predictions${qs ? `?${qs}` : ''}`);
  },
  signals: (params: { limit?: number; decision?: 'BUY' | 'SELL' | 'HOLD' } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.decision) q.set('decision', params.decision);
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
