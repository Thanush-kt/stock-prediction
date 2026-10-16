'use client';

import React from 'react';
import Link from 'next/link';

export function DashboardPreviewSection() {
  return (
    <section className="py-20 lg:py-28 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-emerald-500/5 blur-[150px] rounded-full" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Platform Interface
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            A Unified Command Center for Your Strategy
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Monitor open positions, track signal decisions, review paper order fills, and inspect live portfolio equity curves.
          </p>
        </div>

        {/* Dashboard Frame Mockup */}
        <div className="mt-14 rounded-2xl border border-slate-800 bg-[#0b0f19] shadow-2xl shadow-emerald-950/20 overflow-hidden">
          {/* Top Window Bar */}
          <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-rose-500/80 inline-block" />
              <span className="h-3 w-3 rounded-full bg-amber-500/80 inline-block" />
              <span className="h-3 w-3 rounded-full bg-emerald-500/80 inline-block" />
              <span className="ml-3 text-xs font-mono text-slate-400">
                http://localhost:3000/dashboard
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[11px] font-mono font-medium text-emerald-400">
                LIVE INTERFACE PREVIEW
              </span>
            </div>
          </div>

          {/* Inner Content Area */}
          <div className="p-5 sm:p-7 space-y-6">
            {/* Top Metrics Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-xs uppercase font-mono text-slate-400">Total Equity</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-white mt-1">$104,250.00</div>
                <div className="text-xs text-emerald-400 font-medium mt-0.5">+4.25% cumulative</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-xs uppercase font-mono text-slate-400">Buying Power (Cash)</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-white mt-1">$42,100.00</div>
                <div className="text-xs text-slate-400 font-medium mt-0.5">Unallocated capital</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-xs uppercase font-mono text-slate-400">Capital Exposure</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-white mt-1">59.6%</div>
                <div className="text-xs text-slate-400 font-medium mt-0.5">Max cap: 80.0%</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-xs uppercase font-mono text-slate-400">Risk System Status</div>
                <div className="text-xl sm:text-2xl font-bold font-mono text-emerald-400 mt-1">✓ LIVE ACTIVE</div>
                <div className="text-xs text-slate-400 font-medium mt-0.5">Reconciled</div>
              </div>
            </div>

            {/* Split Row: Chart & Signals Table Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Equity Curve Visual */}
              <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900/40 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-semibold text-white">Equity Curve Performance</h4>
                    <p className="text-xs text-slate-400">Simulated paper-portfolio valuation history</p>
                  </div>
                  <span className="text-xs font-mono text-emerald-400 font-medium">Paper Mode</span>
                </div>

                <div className="h-52 w-full">
                  <svg className="h-full w-full overflow-visible" viewBox="0 0 500 160" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="previewGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M0,140 C50,135 100,120 150,110 C200,100 250,115 300,85 C350,60 400,65 450,35 C480,25 490,20 500,15 L500,160 L0,160 Z"
                      fill="url(#previewGradient)"
                    />
                    <path
                      d="M0,140 C50,135 100,120 150,110 C200,100 250,115 300,85 C350,60 400,65 450,35 C480,25 490,20 500,15"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2.5"
                    />
                  </svg>
                </div>
                <div className="flex justify-between text-[11px] font-mono text-slate-400 mt-2">
                  <span>Day 1: $100,000</span>
                  <span>Day 15: $102,150</span>
                  <span>Day 30: $104,250</span>
                </div>
              </div>

              {/* Signals & Positions Quick Preview */}
              <div className="lg:col-span-5 space-y-4">
                {/* Signals Table */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-300 mb-2.5">
                    Recent Signals Preview
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">AAPL</span>
                        <span className="rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-slate-950">BUY</span>
                      </div>
                      <span className="text-slate-300">Score: 0.742</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">MSFT</span>
                        <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-bold text-slate-300">HOLD</span>
                      </div>
                      <span className="text-slate-300">Score: 0.518</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">NVDA</span>
                        <span className="rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-slate-950">BUY</span>
                      </div>
                      <span className="text-slate-300">Score: 0.812</span>
                    </div>
                  </div>
                </div>

                {/* Open Positions */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <div className="text-xs font-semibold uppercase text-slate-300 mb-2.5">
                    Active Portfolio Positions
                  </div>
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800/80">
                      <span className="font-bold text-white">AAPL · 10 shares</span>
                      <span className="text-emerald-400 font-semibold">$1,894.50</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800/80">
                      <span className="font-bold text-white">NVDA · 5 shares</span>
                      <span className="text-emerald-400 font-semibold">$664.00</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Callout in Preview */}
          <div className="border-t border-slate-800/80 bg-slate-950/90 p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
            <span className="text-xs text-slate-400 font-mono">
              Ready to explore live positions and run model simulations?
            </span>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-400 transition"
            >
              <span>Launch Dashboard Experience</span>
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
