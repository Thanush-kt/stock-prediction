import React from 'react';
import type { EquityPoint } from '@/types/api';

export function SummaryCard({ risk }: { risk: EquityPoint | null }) {
  if (!risk) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 text-sm text-slate-400 flex items-center gap-3">
        <svg className="h-5 w-5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>No risk state recorded yet. Risk metrics will be generated after portfolio reconciliation runs.</span>
      </div>
    );
  }

  const ts = new Date(risk.ts).toLocaleString();

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Equity */}
        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-5 hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>TOTAL EQUITY</span>
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight">
            ${risk.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Portfolio market valuation
          </div>
        </div>

        {/* Buying Power / Cash */}
        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-5 hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>AVAILABLE CASH</span>
            <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </span>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight">
            ${risk.cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Unallocated paper capital
          </div>
        </div>

        {/* Capital Exposure */}
        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-5 hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>CAPITAL EXPOSURE</span>
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
              </svg>
            </span>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight">
            {risk.exposure_pct.toFixed(1)}%
          </div>
          <div className="mt-1 text-xs text-slate-400">
            Active positions allocation
          </div>
        </div>

        {/* Risk System Status */}
        <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-5 hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>CIRCUIT STATUS</span>
            <span className="p-1.5 rounded-lg bg-slate-800 text-slate-300">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${risk.halted ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`} />
            <span className={`text-lg font-bold font-mono ${risk.halted ? 'text-rose-400' : 'text-emerald-400'}`}>
              {risk.halted ? 'HALTED' : 'LIVE ACTIVE'}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-400">
            {risk.halted ? 'Trading suspended' : 'Guardrails operational'}
          </div>
        </div>
      </div>

      <div className="text-right text-[11px] font-mono text-slate-400 pr-1">
        Reconciled as of {ts}
      </div>
    </div>
  );
}
