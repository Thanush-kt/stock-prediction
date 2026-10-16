import React from 'react';

export default function Loading() {
  return (
    <div className="space-y-8 animate-pulse">
      {/* Header skeleton */}
      <div className="space-y-2 border-b border-slate-800/80 pb-5">
        <div className="h-4 w-28 bg-slate-800/60 rounded-full" />
        <div className="h-8 w-56 bg-slate-800 rounded-lg" />
        <div className="h-4 w-80 bg-slate-800/40 rounded-lg" />
      </div>

      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 space-y-3">
            <div className="h-3 w-20 bg-slate-800 rounded" />
            <div className="h-7 w-32 bg-slate-800/80 rounded" />
            <div className="h-3 w-24 bg-slate-800/40 rounded" />
          </div>
        ))}
      </div>

      {/* Table Skeleton */}
      <div className="h-64 rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 space-y-4">
        <div className="h-4 w-36 bg-slate-800 rounded" />
        <div className="space-y-2.5">
          <div className="h-10 w-full bg-slate-800/30 rounded-lg" />
          <div className="h-10 w-full bg-slate-800/30 rounded-lg" />
          <div className="h-10 w-full bg-slate-800/30 rounded-lg" />
        </div>
      </div>
    </div>
  );
}
