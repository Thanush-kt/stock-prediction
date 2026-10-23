'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { RiskAnalysis } from '@/types/api';

interface RiskPanelProps {
  symbol: string;
}

export function RiskPanel({ symbol }: RiskPanelProps) {
  const [risk, setRisk] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api
      .stockRisk(symbol)
      .then((data) => {
        if (mounted) {
          setRisk(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [symbol]);

  const getRiskColor = (cat: string) => {
    switch (cat) {
      case 'LOW':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          indicator: 'bg-emerald-500',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          indicator: 'bg-amber-500',
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
          indicator: 'bg-orange-500',
        };
      case 'VERY HIGH':
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          indicator: 'bg-rose-500',
        };
      default:
        return {
          bg: 'bg-slate-500/10 border-slate-500/30 text-slate-400',
          indicator: 'bg-slate-500',
        };
    }
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl animate-pulse space-y-4">
        <div className="h-6 w-40 bg-slate-800 rounded"></div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="h-20 bg-slate-800/60 rounded-xl"></div>
          <div className="h-20 bg-slate-800/60 rounded-xl"></div>
          <div className="h-20 bg-slate-800/60 rounded-xl"></div>
          <div className="h-20 bg-slate-800/60 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl text-center text-xs text-slate-500">
        Risk metrics unavailable for {symbol}.
      </div>
    );
  }

  const color = getRiskColor(risk.risk_category);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl">
      {/* Risk Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/60 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Quantitative Risk Profile</h3>
            <p className="text-xs text-slate-400">Real-time volatility and execution parameters</p>
          </div>
        </div>

        {/* Risk Category Badge */}
        <div className={`inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-bold tracking-wide ${color.bg}`}>
          <span className={`h-2 w-2 rounded-full ${color.indicator} animate-pulse`}></span>
          <span>{risk.risk_category} RISK</span>
        </div>
      </div>

      {/* Grid of Key Risk Metrics */}
      <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/50 p-3.5">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Hist Vol (20D)</div>
          <div className="mt-1 text-lg font-bold font-mono text-white">
            {risk.hist_volatility_20d !== null ? `${(risk.hist_volatility_20d * 100).toFixed(1)}%` : '—'}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500">Annualized 20-day</div>
        </div>

        <div className="rounded-xl border border-slate-800/60 bg-slate-900/50 p-3.5">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Hist Vol (60D)</div>
          <div className="mt-1 text-lg font-bold font-mono text-white">
            {risk.hist_volatility_60d !== null ? `${(risk.hist_volatility_60d * 100).toFixed(1)}%` : '—'}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500">Annualized 60-day</div>
        </div>

        <div className="rounded-xl border border-slate-800/60 bg-slate-900/50 p-3.5">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">ATR (14-Period)</div>
          <div className="mt-1 text-lg font-bold font-mono text-white">
            {risk.atr_14 !== null ? risk.atr_14.toFixed(2) : '—'}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500">Average True Range</div>
        </div>

        <div className="rounded-xl border border-slate-800/60 bg-slate-900/50 p-3.5">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Max Drawdown (1Y)</div>
          <div className="mt-1 text-lg font-bold font-mono text-rose-400">
            {risk.max_drawdown_1y !== null ? `-${(risk.max_drawdown_1y * 100).toFixed(1)}%` : '—'}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500">Peak-to-trough</div>
        </div>
      </div>

      {/* Execution Targets */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3.5 border-t border-slate-800/40 pt-4">
        <div className="flex flex-col">
          <span className="text-[11px] text-slate-400">Stop-Loss Target</span>
          <span className="text-sm font-bold font-mono text-rose-400">
            -{(risk.stop_loss_pct * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[11px] text-slate-400">Take-Profit Target</span>
          <span className="text-sm font-bold font-mono text-emerald-400">
            +{(risk.take_profit_pct * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[11px] text-slate-400">Risk / Reward Ratio</span>
          <span className="text-sm font-bold font-mono text-white">
            {risk.risk_reward_ratio.toFixed(1)} : 1
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[11px] text-slate-400">Suggested Sizing</span>
          <span className="text-sm font-bold font-mono text-emerald-400">
            {(risk.suggested_position_pct * 100).toFixed(0)}% portfolio
          </span>
        </div>
      </div>

      {/* Narrative Explanation */}
      <div className="mt-4 rounded-xl bg-slate-900/60 p-3 text-xs text-slate-300 border border-slate-800/40 flex items-start gap-2.5">
        <svg className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{risk.risk_explanation}</span>
      </div>
    </div>
  );
}
