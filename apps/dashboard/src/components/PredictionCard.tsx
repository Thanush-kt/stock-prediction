'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { MarketData, SessionPredictionDetail, StockPredictionSessions } from '@/types/api';

interface PredictionCardProps {
  symbol: string;
}

export function PredictionCard({ symbol }: PredictionCardProps) {
  const [sessionData, setSessionData] = useState<StockPredictionSessions | null>(null);
  const [quote, setQuote] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    Promise.allSettled([
      api.predictionSessions({ symbol }),
      api.stockMarketData(symbol),
    ]).then(([sessRes, quoteRes]) => {
      if (!mounted) return;
      if (sessRes.status === 'fulfilled' && sessRes.value.length > 0) {
        setSessionData(sessRes.value[0]);
      } else {
        setSessionData(null);
      }

      if (quoteRes.status === 'fulfilled') {
        setQuote(quoteRes.value);
      }

      if (sessRes.status === 'rejected' && quoteRes.status === 'rejected') {
        setError('Failed to connect to API service.');
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [symbol]);

  const isIndian = symbol.endsWith('.NS') || symbol.endsWith('.BO');
  const currencyPrefix = isIndian ? '₹' : '$';

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl animate-pulse space-y-4">
        <div className="flex justify-between items-center">
          <div className="h-6 w-32 bg-slate-800 rounded"></div>
          <div className="h-6 w-24 bg-slate-800 rounded"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-44 w-full bg-slate-800/60 rounded-xl"></div>
          <div className="h-44 w-full bg-slate-800/60 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error || !sessionData) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl text-center space-y-3">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800/60 text-slate-400">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div className="text-sm font-semibold text-slate-300">No Prediction Available for {symbol}</div>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          {error || `Run batch inference with 'stockpred predict' to generate session forecasts for ${symbol}.`}
        </p>
      </div>
    );
  }

  const effectiveQuote = quote || sessionData.latest_quote;

  const renderSessionBox = (
    title: string,
    subtitle: string,
    detail: SessionPredictionDetail,
    isNextSession: boolean = false
  ) => {
    const pred = detail.prediction;
    const targetDateFormatted = detail.target_session
      ? new Date(detail.target_session + 'T00:00:00').toLocaleDateString(undefined, {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        })
      : 'Session Date Unavailable';

    if (!pred || detail.status === 'unavailable' || detail.status === 'pending_close') {
      return (
        <div className="flex flex-col justify-between rounded-xl border border-slate-800/60 bg-slate-900/40 p-4 min-h-[220px]">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800/40 pb-2.5">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                  {title}
                </span>
                <div className="text-xs font-semibold text-white mt-0.5">{targetDateFormatted}</div>
              </div>
              <span className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-mono font-medium text-amber-400">
                {detail.status === 'pending_close' ? '⏳ Pending Session Close' : '⚡ Awaiting Ingest'}
              </span>
            </div>
            <div className="py-6 text-center">
              <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/40 text-slate-400 mb-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-xs text-slate-400 max-w-[240px] mx-auto">
                {detail.message || (isNextSession
                  ? 'Next session forecast will generate once current trading day wraps up.'
                  : 'No valid prediction found for this session.')}
              </p>
            </div>
          </div>
          <div className="text-[11px] text-slate-500 font-mono text-center border-t border-slate-800/30 pt-2">
            Status: {detail.status}
          </div>
        </div>
      );
    }

    const isUp = pred.label_pred === 1;
    const confidencePct = (pred.score * 100).toFixed(1);
    const cutoffFormatted = new Date(pred.data_cutoff_ts || pred.ts).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });

    const timingBadge = () => {
      if (detail.timing === 'before_session') {
        return (
          <span className="rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-mono text-blue-400">
            Pre-Market Run
          </span>
        );
      }
      if (detail.timing === 'during_session') {
        return (
          <span className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
            Intraday Run
          </span>
        );
      }
      return (
        <span className="rounded-md bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-mono text-purple-400">
          Next Session Forecast
        </span>
      );
    };

    return (
      <div className="flex flex-col justify-between rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 min-h-[220px]">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800/60 pb-2.5">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 font-mono">
                  {title}
                </span>
                {timingBadge()}
              </div>
              <div className="text-xs font-bold text-white mt-0.5">{targetDateFormatted}</div>
            </div>
            <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
              {pred.model_version}
            </span>
          </div>

          {/* Direction & Probability */}
          <div className="mt-3.5 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                Direction Forecast
              </div>
              <div className="mt-1">
                {isUp ? (
                  <div className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-1 text-xs font-bold text-emerald-400">
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                    <span>BULLISH (UP)</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 px-2.5 py-1 text-xs font-bold text-rose-400">
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                    <span>BEARISH (DOWN)</span>
                  </div>
                )}
              </div>
            </div>

            <div className="text-right">
              <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Model Probability</div>
              <div className="mt-1 text-sm font-bold font-mono text-white">{confidencePct}%</div>
            </div>
          </div>

          {/* Probability Bar */}
          <div className="mt-3">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isUp ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, Number(confidencePct)))}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Footer: Cutoff & Outcome */}
        <div className="mt-3.5 flex items-center justify-between border-t border-slate-800/40 pt-2.5 text-[11px]">
          <div className="text-slate-400 truncate max-w-[150px]">
            Cutoff: <span className="font-mono text-slate-300">{cutoffFormatted}</span>
          </div>

          <div>
            {pred.actual_label !== null && pred.actual_label !== undefined ? (
              <span
                className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold font-mono ${
                  pred.actual_label === pred.label_pred
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                }`}
              >
                {pred.actual_label === pred.label_pred ? '✓ HIT' : '✗ MISS'}
                {typeof pred.actual_close === 'number' && ` (${currencyPrefix}${pred.actual_close.toFixed(2)})`}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium text-slate-400 font-mono">
                ⏳ Outcome Pending
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl">
      {/* Top Banner: Symbol, Exchange & Real-time Quote */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800/60 pb-4 gap-3">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold font-mono tracking-tight text-white">{symbol}</span>
              <span className="rounded-md bg-slate-800/80 px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-300 border border-slate-700/50">
                {sessionData.exchange}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-mono font-medium ${
                  sessionData.is_market_open
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${sessionData.is_market_open ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
                {sessionData.is_market_open ? 'Market Open' : 'Market Closed'}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">
              Exchange TZ: {sessionData.exchange_timezone}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {effectiveQuote && (
            <div className="text-right">
              <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider font-mono">
                Live Price
              </div>
              <div className="text-lg font-bold font-mono text-white leading-tight">
                {currencyPrefix}
                {effectiveQuote.price.toFixed(2)}
              </div>
              {effectiveQuote.change_pct !== null && effectiveQuote.change_pct !== undefined && (
                <div
                  className={`text-[11px] font-bold font-mono leading-none ${
                    effectiveQuote.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {effectiveQuote.change_pct >= 0 ? '+' : ''}
                  {effectiveQuote.change_pct.toFixed(2)}%
                </div>
              )}
            </div>
          )}

          <Link
            href={`/stocks/${encodeURIComponent(symbol)}`}
            className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:bg-slate-800 transition flex items-center gap-1.5"
          >
            <span>Details</span>
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </div>

      {/* Dual Session Display: Today's Prediction & Tomorrow's Prediction */}
      <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        {renderSessionBox(
          "Today's Trading Session",
          sessionData.current_session_date,
          sessionData.today,
          false
        )}
        {renderSessionBox(
          "Tomorrow's Trading Session",
          sessionData.next_session_date,
          sessionData.tomorrow,
          true
        )}
      </div>
    </div>
  );
}
