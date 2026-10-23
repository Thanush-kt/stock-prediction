import React from 'react';
import { api } from '@/lib/api';
import { PredictionsDashboardView } from '@/components/PredictionsDashboardView';
import { ErrorMessage } from '@/components/ErrorMessage';
import type { Prediction } from '@/types/api';

export default async function PredictionsPage() {
  let predictions: Prediction[] | null = null;
  let error: string | null = null;

  try {
    predictions = await api.predictions({ limit: 100 });
  } catch {
    error = 'Could not load model predictions. Ensure the backend API service is running on port 8000.';
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
            Quantitative Inference
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Model Predictions
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Inference scores, return probabilities, and direction forecasts produced by trained walk-forward machine learning models.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            Feature Vector Stream
          </span>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {predictions ? (
        <PredictionsDashboardView initialPredictions={predictions} />
      ) : !error ? (
        <PredictionsDashboardView initialPredictions={[]} />
      ) : null}
    </div>
  );
}
