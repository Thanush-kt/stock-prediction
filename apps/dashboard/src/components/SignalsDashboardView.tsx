'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Signal } from '@/types/api';
import { StockSelector } from './StockSelector';
import { SignalsTable } from './SignalsTable';

interface SignalsDashboardViewProps {
  initialSignals: Signal[];
}

export function SignalsDashboardView({ initialSignals }: SignalsDashboardViewProps) {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [signals, setSignals] = useState<Signal[]>(initialSignals);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    api
      .signals({ limit: 50, symbol: selectedSymbol || undefined })
      .then((data) => {
        if (mounted) {
          setSignals(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [selectedSymbol]);

  return (
    <div className="space-y-6">
      {/* Filter Toolbar */}
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-5 shadow-xl backdrop-blur-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight">Filter Signals by Asset</h2>
          <p className="text-xs text-slate-400">View execution conviction decisions for specific equities or instruments</p>
        </div>
        <div className="flex items-center gap-3">
          <StockSelector selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
          {selectedSymbol && (
            <button
              type="button"
              onClick={() => setSelectedSymbol(null)}
              className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-mono text-slate-400 hover:text-white transition"
            >
              Clear Filter
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-12 text-center text-xs text-slate-400">
          <div className="flex items-center justify-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></div>
            <span>Loading signals for {selectedSymbol}...</span>
          </div>
        </div>
      ) : (
        <SignalsTable signals={signals} />
      )}
    </div>
  );
}
