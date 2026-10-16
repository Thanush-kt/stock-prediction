import React from 'react';
import { api } from '@/lib/api';
import { EquityChart } from '@/components/EquityChart';
import { ErrorMessage } from '@/components/ErrorMessage';
import type { EquityPoint } from '@/types/api';

export default async function EquityPage() {
  let data: EquityPoint[] | null = null;
  let error: string | null = null;

  try {
    data = await api.equity();
  } catch {
    error = 'Could not load equity curve data. Ensure the backend API service is running on port 8000.';
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Performance Metrics
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Equity Curve
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Cumulative mark-to-market portfolio equity history and capital drawdowns over time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            Mark-to-Market
          </span>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {data && <EquityChart data={data} />}
    </div>
  );
}
