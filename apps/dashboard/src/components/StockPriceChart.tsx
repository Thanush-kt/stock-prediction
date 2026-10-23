'use client';

import React, { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '@/lib/api';
import type { MarketData, PriceBar } from '@/types/api';

interface StockPriceChartProps {
  symbol: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: { date: string; close: number; volume: number; high: number; low: number } }>;
  label?: string;
  currencyPrefix: string;
}

function CustomPriceTooltip({ active, payload, label, currencyPrefix }: CustomTooltipProps) {
  if (active && payload && payload.length > 0) {
    const d = payload[0].payload;
    return (
      <div className="rounded-xl border border-slate-800 bg-[#0d131f]/95 p-3.5 shadow-2xl backdrop-blur-md text-xs font-mono space-y-1.5">
        <div className="text-slate-400 font-medium">{label}</div>
        <div className="flex items-center justify-between gap-6">
          <span className="text-slate-400">Close:</span>
          <span className="text-emerald-400 font-bold">
            {currencyPrefix}
            {d.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span className="text-slate-400">Range (H/L):</span>
          <span className="text-slate-200">
            {currencyPrefix}{d.high.toFixed(2)} - {currencyPrefix}{d.low.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span className="text-slate-400">Volume:</span>
          <span className="text-slate-400">{d.volume.toLocaleString()}</span>
        </div>
      </div>
    );
  }
  return null;
}

export function StockPriceChart({ symbol }: StockPriceChartProps) {
  const [days, setDays] = useState<number>(90);
  const [bars, setBars] = useState<PriceBar[]>([]);
  const [quote, setQuote] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const isIndian = symbol.endsWith('.NS') || symbol.endsWith('.BO');
  const currencyPrefix = isIndian ? '₹' : '$';

  useEffect(() => {
    let mounted = true;

    Promise.allSettled([
      api.stockPriceHistory(symbol, days),
      api.stockMarketData(symbol),
    ]).then(([historyRes, quoteRes]) => {
      if (!mounted) return;
      if (historyRes.status === 'fulfilled') {
        setBars(historyRes.value);
      } else {
        setBars([]);
      }
      if (quoteRes.status === 'fulfilled') {
        setQuote(quoteRes.value);
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [symbol, days]);

  const chartData = bars.map((b) => {
    const d = new Date(b.ts);
    return {
      date: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: '2-digit' }),
      close: b.close,
      high: b.high,
      low: b.low,
      volume: b.volume,
    };
  });

  const minClose = chartData.length > 0 ? Math.min(...chartData.map((d) => d.close)) * 0.98 : 0;
  const maxClose = chartData.length > 0 ? Math.max(...chartData.map((d) => d.close)) * 1.02 : 100;

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl">
      {/* Chart Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/60 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="text-lg font-bold tracking-tight text-white font-mono">{symbol}</h3>
            {quote && (
              <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-400">
                {quote.source === 'live' ? '🟢 LIVE' : '🕒 EOD'}
              </span>
            )}
          </div>
          {quote && (
            <div className="mt-1 flex items-baseline gap-2.5">
              <span className="text-2xl font-black tracking-tight text-white font-mono">
                {currencyPrefix}
                {quote.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              {quote.change_pct !== null && quote.change_pct !== undefined && (
                <span
                  className={`text-xs font-bold font-mono ${
                    quote.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {quote.change_pct >= 0 ? '▲ +' : '▼ '}
                  {quote.change_pct.toFixed(2)}%
                </span>
              )}
            </div>
          )}
        </div>

        {/* Timeframe Filters */}
        <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1 text-xs font-medium">
          {[
            { label: '30D', value: 30 },
            { label: '90D', value: 90 },
            { label: '1Y', value: 365 },
          ].map((tf) => (
            <button
              key={tf.value}
              type="button"
              onClick={() => setDays(tf.value)}
              className={`rounded-lg px-3 py-1 transition ${
                days === tf.value
                  ? 'bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="mt-6 h-72 w-full">
        {loading ? (
          <div className="flex h-full items-center justify-center text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></div>
              <span>Loading price history...</span>
            </div>
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center space-y-2 text-center text-xs text-slate-500">
            <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p>No historical price bars recorded for {symbol} yet.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`priceGradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                minTickGap={28}
              />
              <YAxis
                domain={[minClose, maxClose]}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${currencyPrefix}${val.toFixed(0)}`}
                orientation="right"
              />
              <Tooltip
                content={<CustomPriceTooltip currencyPrefix={currencyPrefix} />}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#priceGradient-${symbol})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
