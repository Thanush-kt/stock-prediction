import React from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { PredictionCard } from '@/components/PredictionCard';
import { RiskPanel } from '@/components/RiskPanel';
import { StockPriceChart } from '@/components/StockPriceChart';
import { SignalsTable } from '@/components/SignalsTable';
import { PredictionsTable } from '@/components/PredictionsTable';
import type { Prediction, Signal } from '@/types/api';

interface StockDetailPageProps {
  params: Promise<{ symbol: string }>;
}

export default async function StockDetailPage({ params }: StockDetailPageProps) {
  const resolvedParams = await params;
  const symbol = decodeURIComponent(resolvedParams.symbol).toUpperCase();

  let predictions: Prediction[] = [];
  let signals: Signal[] = [];

  try {
    const [pRes, sRes] = await Promise.allSettled([
      api.predictions({ symbol, limit: 30 }),
      api.signals({ symbol, limit: 30 }),
    ]);
    if (pRes.status === 'fulfilled') predictions = pRes.value;
    if (sRes.status === 'fulfilled') signals = sRes.value;
  } catch {
    // Graceful fallback to empty streams
  }

  const isIndian = symbol.endsWith('.NS') || symbol.endsWith('.BO');
  const isCrypto = symbol.endsWith('-USD') || symbol.includes('-USD');
  const isCommodity = symbol.endsWith('=F');

  const exchangeLabel = isIndian
    ? '🇮🇳 National Stock Exchange of India (NSE)'
    : isCrypto
    ? '🪙 Cryptocurrency Market'
    : isCommodity
    ? '📦 Commodity Futures'
    : '🇺🇸 US Equity Market (NYSE/NASDAQ)';

  return (
    <div className="space-y-8">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
        <Link href="/stocks" className="hover:text-emerald-400 transition">
          Stocks
        </Link>
        <span>/</span>
        <span className="text-white font-bold">{symbol}</span>
      </div>

      {/* Symbol Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
            {exchangeLabel}
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white mt-1 font-mono">
            {symbol}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Machine learning inference, quantitative risk analytics, and execution signal telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/stocks"
            className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition"
          >
            ← All Assets
          </Link>
        </div>
      </div>

      {/* Top Section: Prediction Spotlight & Quantitative Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PredictionCard symbol={symbol} />
        <RiskPanel symbol={symbol} />
      </div>

      {/* Historical Price Chart */}
      <StockPriceChart symbol={symbol} />

      {/* Symbol-Specific Telemetry Streams */}
      <div className="space-y-8 pt-4">
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-white tracking-tight">Signal Execution Decisions</h2>
            <p className="text-xs text-slate-400">Past model conviction orders and risk management actions for {symbol}</p>
          </div>
          <SignalsTable signals={signals} />
        </div>

        <div>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-white tracking-tight">Historical Direction Forecasts</h2>
            <p className="text-xs text-slate-400">Walk-forward inference history and realized session outcomes for {symbol}</p>
          </div>
          <PredictionsTable initialPredictions={predictions} />
        </div>
      </div>
    </div>
  );
}
