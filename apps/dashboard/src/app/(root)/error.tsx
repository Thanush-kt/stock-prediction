'use client';

import React from 'react';

export default function ErrorBoundary({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-2xl border border-rose-900/50 bg-gradient-to-r from-rose-950/40 to-slate-900/60 p-8 max-w-xl mx-auto my-12 space-y-5 text-center shadow-2xl backdrop-blur-md">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>

      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">Something Went Wrong</h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-300 leading-relaxed">
          An error occurred while loading this view. The backend API service may be unavailable or experiencing issues.
        </p>
      </div>

      <div className="pt-2">
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center gap-2 rounded-xl bg-rose-600 hover:bg-rose-500 px-5 py-2.5 text-xs font-mono font-semibold text-white shadow-lg transition cursor-pointer"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Try Again</span>
        </button>
      </div>
    </div>
  );
}
