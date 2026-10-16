'use client';

import React, { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Prediction } from '@/types/api';

interface PredictionsTableProps {
  initialPredictions: Prediction[];
}

export function PredictionsTable({ initialPredictions }: PredictionsTableProps) {
  const [predictions, setPredictions] = useState<Prediction[]>(initialPredictions);
  const [search, setSearch] = useState('');
  const [directionFilter, setDirectionFilter] = useState<'all' | '1' | '0'>('all');
  const [modelVersionFilter, setModelVersionFilter] = useState('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const availableModelVersions = useMemo(() => {
    const set = new Set<string>();
    for (const p of predictions) {
      if (p.model_version) set.add(p.model_version);
    }
    return Array.from(set).sort();
  }, [predictions]);

  const filteredPredictions = useMemo(() => {
    const q = search.trim().toLowerCase();
    return predictions.filter((p) => {
      if (q && !p.symbol.toLowerCase().includes(q)) {
        return false;
      }
      if (directionFilter !== 'all' && String(p.label_pred) !== directionFilter) {
        return false;
      }
      if (modelVersionFilter !== 'all' && p.model_version !== modelVersionFilter) {
        return false;
      }
      return true;
    });
  }, [predictions, search, directionFilter, modelVersionFilter]);

  async function handleRefresh() {
    setIsRefreshing(true);
    setRefreshError(null);
    try {
      const updated = await api.predictions({ limit: 100 });
      setPredictions(updated);
    } catch {
      setRefreshError('Failed to refresh predictions. Check that the API server is reachable.');
    } finally {
      setIsRefreshing(false);
    }
  }

  function handleResetFilters() {
    setSearch('');
    setDirectionFilter('all');
    setModelVersionFilter('all');
  }

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-sm">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search ticker (e.g. MSFT)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 pl-9 pr-3 py-2 text-xs font-mono text-white placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition"
            />
          </div>

          {/* Filters & Refresh */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Direction Filter */}
            <select
              value={directionFilter}
              onChange={(e) => setDirectionFilter(e.target.value as 'all' | '1' | '0')}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-mono text-slate-300 focus:border-emerald-500 focus:outline-none transition cursor-pointer"
            >
              <option value="all">Direction: All</option>
              <option value="1">Direction: Up (1)</option>
              <option value="0">Direction: Down (0)</option>
            </select>

            {/* Model Version Filter */}
            <select
              value={modelVersionFilter}
              onChange={(e) => setModelVersionFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-mono text-slate-300 focus:border-emerald-500 focus:outline-none transition cursor-pointer"
            >
              <option value="all">Model: All Versions</option>
              {availableModelVersions.map((mv) => (
                <option key={mv} value={mv}>
                  Model: {mv}
                </option>
              ))}
            </select>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950/80 hover:bg-slate-800/80 px-3.5 py-2 text-xs font-mono font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50 transition cursor-pointer"
            >
              <svg
                className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>

        {refreshError && (
          <div className="text-xs text-rose-400 font-mono bg-rose-950/20 p-2 rounded-lg border border-rose-900/30">
            {refreshError}
          </div>
        )}
      </div>

      {/* Predictions Table Container */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 overflow-hidden shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/60 px-5 py-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-white tracking-tight">Inference Score Stream</h3>
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono font-medium text-emerald-400">
              {filteredPredictions.length} Predictions
            </span>
          </div>
          {(search || directionFilter !== 'all' || modelVersionFilter !== 'all') && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-mono text-slate-400 hover:text-white underline cursor-pointer"
            >
              Reset Filters
            </button>
          )}
        </div>

        {filteredPredictions.length === 0 ? (
          <div className="p-8 text-center space-y-2">
            <div className="text-sm font-semibold text-slate-300">No predictions matching filters</div>
            <p className="text-xs text-slate-400">Try adjusting your symbol or model version filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse min-w-[750px]">
              <thead>
                <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-5">Timestamp</th>
                  <th className="py-3 px-5">Symbol</th>
                  <th className="py-3 px-5">Forecast Direction</th>
                  <th className="py-3 px-5 text-right">Probability (Confidence)</th>
                  <th className="py-3 px-5">Model Version</th>
                  <th className="py-3 px-5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPredictions.map((p) => {
                  const isExpanded = expandedId === p.id;
                  const isUp = p.label_pred === 1;
                  const scoreVal = typeof p.score === 'number' ? p.score : 0.5;
                  const scoreFormatted = scoreVal.toFixed(3);
                  const meterPct = Math.min(Math.max(scoreVal * 100, 5), 100);

                  return (
                    <React.Fragment key={p.id}>
                      <tr className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3.5 px-5 font-mono text-xs text-slate-400">
                          {new Date(p.ts).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-5">
                          <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold font-mono text-xs">
                            {p.symbol}
                          </span>
                        </td>
                        <td className="py-3.5 px-5">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold ${
                              isUp
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            <span>{isUp ? '↑ UP' : '↓ DOWN'}</span>
                            <span className="text-[10px] opacity-70">({p.label_pred})</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-5 text-right font-mono">
                          <div className="flex items-center justify-end gap-2.5">
                            <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${isUp ? 'bg-emerald-400' : 'bg-amber-400'}`}
                                style={{ width: `${meterPct}%` }}
                              />
                            </div>
                            <span className="font-semibold text-white">{scoreFormatted}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-5">
                          <span className="text-xs font-mono text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700/60">
                            {p.model_version}
                          </span>
                        </td>
                        <td className="py-3.5 px-5 text-right">
                          <button
                            type="button"
                            onClick={() => setExpandedId(isExpanded ? null : p.id)}
                            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer transition"
                          >
                            {isExpanded ? 'Hide' : 'Inspect'}
                          </button>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={6} className="bg-slate-950/90 px-6 py-4 border-b border-slate-800/80">
                            <div className="rounded-xl border border-slate-800 bg-[#060910] p-4 text-xs font-mono space-y-2">
                              <div className="text-[11px] uppercase tracking-wider text-slate-400">
                                Model Prediction Record Metadata
                              </div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-slate-300 pt-2 border-t border-slate-800/60">
                                <div>
                                  <span className="text-slate-400">Prediction ID:</span>
                                  <div className="text-white mt-0.5">#{p.id}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Target Direction:</span>
                                  <div className="text-emerald-400 font-bold mt-0.5">{isUp ? 'UP (Class 1)' : 'DOWN (Class 0)'}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Raw Model Score:</span>
                                  <div className="text-white mt-0.5">{p.score}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Model Version Tag:</span>
                                  <div className="text-white mt-0.5">{p.model_version}</div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
