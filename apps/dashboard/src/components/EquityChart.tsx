'use client';

import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { EquityPoint } from '@/types/api';

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: { ts: string; equity: number; cash?: number; exposure?: number } }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (active && payload && payload.length > 0) {
    const d = payload[0].payload;
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/95 p-3.5 shadow-2xl backdrop-blur-md text-xs font-mono space-y-1.5">
        <div className="text-slate-400 font-medium">{label}</div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-slate-400">Equity:</span>
          <span className="text-emerald-400 font-bold">${d.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        {d.cash !== undefined && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">Cash:</span>
            <span className="text-slate-200">${d.cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
        )}
      </div>
    );
  }
  return null;
}

export function EquityChart({ data }: { data: EquityPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-12 text-center space-y-3">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800/60 text-slate-400">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <div className="text-base font-semibold text-slate-200">No Equity History Recorded</div>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Historical valuation points will be generated after portfolio reconciliations run.
        </p>
      </div>
    );
  }

  const series = data.map((d) => ({
    ts: new Date(d.ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    equity: d.equity,
    cash: d.cash,
    exposure: d.exposure_pct,
  }));

  const latestEquity = data[data.length - 1].equity;
  const startingEquity = data[0].equity;
  const totalChange = latestEquity - startingEquity;
  const totalChangePct = startingEquity > 0 ? (totalChange / startingEquity) * 100 : 0;
  const isPositive = totalChange >= 0;

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 overflow-hidden shadow-xl p-5 sm:p-6 space-y-6">
      {/* Chart Header Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-mono uppercase text-slate-400">Latest Portfolio Valuation</div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="text-3xl font-bold font-mono text-white tracking-tight">
              ${latestEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
              <span>{isPositive ? '+' : ''}{totalChange.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              <span>({isPositive ? '+' : ''}{totalChangePct.toFixed(2)}%)</span>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div>
            <span>Data Points: </span>
            <span className="text-white font-medium">{data.length}</span>
          </div>
          <div>
            <span>Mode: </span>
            <span className="text-emerald-400 font-medium">Alpaca Paper</span>
          </div>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="w-full h-80 sm:h-96">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} vertical={false} />
            <XAxis dataKey="ts" stroke="#64748b" fontSize={11} minTickGap={30} tickLine={false} />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              width={75}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `$${Number(v).toLocaleString()}`}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#10b981"
              strokeWidth={2.5}
              fill="url(#equityGradient)"
              activeDot={{ r: 5, fill: '#10b981', stroke: '#080c14', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
