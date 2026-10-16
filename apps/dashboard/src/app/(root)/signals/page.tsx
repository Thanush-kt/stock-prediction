import React from 'react';
import { api } from '@/lib/api';
import { SignalsTable } from '@/components/SignalsTable';
import { ErrorMessage } from '@/components/ErrorMessage';
import type { Signal } from '@/types/api';

export default async function SignalsPage() {
  let signals: Signal[] | null = null;
  let error: string | null = null;

  try {
    signals = await api.signals({ limit: 50 });
  } catch {
    error = 'Could not load trading signals. Ensure the backend API service is running on port 8000.';
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Disciplined Execution
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Strategy Signals
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Deterministic BUY, SELL, or HOLD decisions evaluated against strategy conviction and risk threshold controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            Conviction Rules Active
          </span>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {signals ? (
        <SignalsTable signals={signals} />
      ) : !error ? (
        <SignalsTable signals={[]} />
      ) : null}
    </div>
  );
}
