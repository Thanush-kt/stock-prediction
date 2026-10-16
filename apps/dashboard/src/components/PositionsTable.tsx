import React from 'react';
import type { Position } from '@/types/api';

export function PositionsTable({ positions }: { positions: Position[] }) {
  if (positions.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-8 text-center space-y-3">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800/60 text-slate-400">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <div className="text-base font-semibold text-slate-200">No Open Positions</div>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Your portfolio currently holds 0 active positions. New positions will appear once simulated signals are executed.
        </p>
      </div>
    );
  }

  const totalNotional = positions.reduce((acc, p) => acc + p.qty * p.avg_price, 0);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 overflow-hidden shadow-xl">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800/80 bg-slate-950/60 px-5 py-4 gap-2">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-white tracking-tight">Active Holdings</h3>
          <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono font-medium text-emerald-400">
            {positions.length} {positions.length === 1 ? 'Holding' : 'Holdings'}
          </span>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Total Value: <span className="text-white font-semibold">${totalNotional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-5">Symbol</th>
              <th className="py-3 px-5 text-right">Quantity</th>
              <th className="py-3 px-5 text-right">Avg Entry Price</th>
              <th className="py-3 px-5 text-right">Notional Value</th>
              <th className="py-3 px-5">Broker Source</th>
              <th className="py-3 px-5 text-right">Last Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {positions.map((p) => {
              const notional = p.qty * p.avg_price;
              return (
                <tr key={p.symbol} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-5">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold font-mono text-xs">
                      {p.symbol}
                    </span>
                  </td>
                  <td className="py-3.5 px-5 text-right font-mono font-medium text-slate-200">
                    {p.qty.toLocaleString()}
                  </td>
                  <td className="py-3.5 px-5 text-right font-mono text-slate-300">
                    ${p.avg_price.toFixed(2)}
                  </td>
                  <td className="py-3.5 px-5 text-right font-mono font-semibold text-white">
                    ${notional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="py-3.5 px-5">
                    <span className="text-xs font-mono uppercase text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/60">
                      {p.source}
                    </span>
                  </td>
                  <td className="py-3.5 px-5 text-right font-mono text-xs text-slate-400">
                    {new Date(p.updated_at).toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
