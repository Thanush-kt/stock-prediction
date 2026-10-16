import React from 'react';
import { api } from '@/lib/api';
import { PositionsTable } from '@/components/PositionsTable';
import { SummaryCard } from '@/components/SummaryCard';
import { ErrorMessage } from '@/components/ErrorMessage';
import type { Position, EquityPoint } from '@/types/api';

export default async function Dashboard() {
  let positions: Position[] | null = null;
  let equity: EquityPoint[] | null = null;
  let error: string | null = null;

  try {
    [positions, equity] = await Promise.all([
      api.positions(),
      api.equity(),
    ]);
  } catch {
    error = 'Could not load portfolio data. Ensure the backend API service is running on port 8000.';
  }

  const latestRisk = equity && equity.length > 0 ? equity[equity.length - 1] : null;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Portfolio & Risk Command
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Trading Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Live simulated portfolio metrics, cash allocation, and active holdings reconciled with the broker sandbox.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            Alpaca Paper Sandbox
          </span>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {/* Summary Metrics */}
      <SummaryCard risk={latestRisk} />

      {/* Positions Section */}
      <div className="pt-2">
        {positions ? (
          <PositionsTable positions={positions} />
        ) : !error ? (
          <PositionsTable positions={[]} />
        ) : null}
      </div>
    </div>
  );
}