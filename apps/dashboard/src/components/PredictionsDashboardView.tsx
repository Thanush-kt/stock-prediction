'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Prediction, PredictionAccuracy } from '@/types/api';
import { StockSelector } from './StockSelector';
import { PredictionCard } from './PredictionCard';
import { PredictionsTable } from './PredictionsTable';

interface PredictionsDashboardViewProps {
  initialPredictions: Prediction[];
}

export function PredictionsDashboardView({ initialPredictions }: PredictionsDashboardViewProps) {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>('AAPL');
  const [accuracy, setAccuracy] = useState<PredictionAccuracy | null>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(false);

  useEffect(() => {
    if (!selectedSymbol) return;
    let mounted = true;
    api
      .predictionAccuracy({ symbol: selectedSymbol, days: 90 })
      .then((data) => {
        if (mounted) {
          setAccuracy(data.length > 0 ? data[0] : null);
          setAccuracyLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setAccuracyLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [selectedSymbol]);

  const displayedAccuracy = selectedSymbol ? accuracy : null;

  return (
    <div className="space-y-6">
      {/* Stock Selection Bar */}
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-5 shadow-xl backdrop-blur-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight">Per-Asset Direction Forecasts</h2>
          <p className="text-xs text-slate-400">Select any equity, NSE stock, or crypto asset to inspect session forecasts</p>
        </div>
        <div className="flex items-center gap-3">
          <StockSelector selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
          {selectedSymbol && (
            <button
              type="button"
              onClick={() => setSelectedSymbol(null)}
              className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-mono text-slate-400 hover:text-white transition"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Selected Stock Spotlight */}
      {selectedSymbol && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <PredictionCard symbol={selectedSymbol} />
          </div>
          <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl flex flex-col justify-between">
            <div className="border-b border-slate-800/60 pb-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400 font-mono">
                Model Performance
              </span>
              <h3 className="text-base font-bold text-white tracking-tight mt-0.5">
                90-Day Realized Accuracy
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Historical directional hit rate</p>
            </div>

            <div className="py-6 text-center space-y-1">
              {accuracyLoading ? (
                <div className="h-10 w-24 mx-auto bg-slate-800 rounded animate-pulse"></div>
              ) : displayedAccuracy ? (
                <>
                  <div className="text-4xl font-black font-mono tracking-tight text-white">
                    {(displayedAccuracy.accuracy * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    {displayedAccuracy.n_correct} correct of {displayedAccuracy.n_evaluated} evaluated sessions
                  </div>
                </>
              ) : (
                <div className="text-xs text-slate-500 py-3">
                  No evaluated outcome sessions recorded yet in past 90 days.
                </div>
              )}
            </div>

            <div className="rounded-xl bg-slate-900/60 border border-slate-800/40 p-3 text-[11px] text-slate-400 font-mono flex items-center justify-between">
              <span>Evaluated Target Sessions:</span>
              <span className="text-white font-bold">{accuracy ? accuracy.n_evaluated : 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Predictions Stream Table */}
      <PredictionsTable initialPredictions={initialPredictions} />
    </div>
  );
}
