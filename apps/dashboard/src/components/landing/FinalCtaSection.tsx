import React from 'react';
import Link from 'next/link';

export function FinalCtaSection() {
  return (
    <section className="py-20 lg:py-28 relative overflow-hidden border-t border-slate-800/80">
      {/* Background Emerald Radial Glow */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="w-[600px] h-[300px] bg-emerald-500/10 blur-[130px] rounded-full" />
      </div>

      <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-medium text-emerald-400 mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
          <span>Start Experimenting Today</span>
        </div>

        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Explore a Smarter Way to{' '}
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
            Analyze Stocks.
          </span>
        </h2>

        <p className="mt-4 max-w-2xl mx-auto text-base sm:text-lg text-slate-300 leading-relaxed">
          Explore machine-learning predictions, review trading signals, and experiment with paper trading in one integrated dashboard.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-7 py-3.5 text-base font-semibold text-slate-950 shadow-[0_0_25px_rgba(16,185,129,0.3)] hover:bg-emerald-400 hover:shadow-[0_0_35px_rgba(16,185,129,0.45)] transition-all"
          >
            <span>Open Dashboard</span>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
          <Link
            href="/sign-up"
            className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/80 px-7 py-3.5 text-base font-medium text-slate-200 hover:border-slate-600 hover:bg-slate-800 transition-all"
          >
            Get Started
          </Link>
        </div>
      </div>
    </section>
  );
}
