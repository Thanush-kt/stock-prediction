'use client';

import React from 'react';

interface ErrorMessageProps {
  message?: string;
}

export function ErrorMessage({
  message = 'Failed to load data from the API server. Please verify that the backend service is running on port 8000.',
}: ErrorMessageProps) {
  return (
    <div className="rounded-2xl border border-rose-900/40 bg-gradient-to-r from-rose-950/30 to-slate-900/50 p-5 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md shadow-lg shadow-rose-950/10">
      <div className="flex items-start gap-3.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 mt-0.5">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div>
          <h4 className="font-semibold text-white tracking-tight">API Connection Interrupted</h4>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed">{message}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="self-start sm:self-auto shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-rose-800/80 bg-rose-950/50 hover:bg-rose-900/60 px-4 py-2 text-xs font-mono font-semibold text-rose-200 transition cursor-pointer"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span>Retry Connection</span>
      </button>
    </div>
  );
}
