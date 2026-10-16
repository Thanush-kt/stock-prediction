'use client';

import React, { useState } from 'react';
import Link from 'next/link';

export function HeroSection() {
  const [selectedRange, setSelectedRange] = useState<'1D' | '1W' | '1M' | '1Y'>('1M');

  return (
    <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-28">
      {/* Background Glows */}
      <div className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-emerald-500/10 blur-[130px] rounded-full" />
      <div className="pointer-events-none absolute top-1/3 right-10 w-[400px] h-[300px] bg-cyan-500/5 blur-[120px] rounded-full" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Headlines & CTA */}
          <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
            {/* Tag Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-medium text-emerald-400">
              <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              <span>Machine Learning & Paper-Trading Engine</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
              Turn Market Data Into{' '}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                Smarter Decisions.
              </span>
            </h1>

            {/* Description */}
            <p className="max-w-2xl text-base sm:text-lg text-slate-300 leading-relaxed mx-auto lg:mx-0">
              Explore machine-learning-driven stock predictions, trading signals, and portfolio insights through one integrated platform designed to help you analyze the market with greater clarity.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3.5 pt-2">
              <Link
                href="/dashboard"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 text-base font-semibold text-slate-950 shadow-[0_0_25px_rgba(16,185,129,0.25)] hover:bg-emerald-400 hover:shadow-[0_0_35px_rgba(16,185,129,0.4)] transition-all"
              >
                <span>Explore Dashboard</span>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </Link>
              <Link
                href="#how-it-works"
                className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900/60 px-6 py-3.5 text-base font-medium text-slate-200 hover:border-slate-600 hover:bg-slate-800/80 transition-all"
              >
                How It Works
              </Link>
            </div>

            {/* Trust Highlights */}
            <div className="pt-6 border-t border-slate-800/80 grid grid-cols-3 gap-4 text-left">
              <div>
                <div className="text-xs text-slate-400">Architecture</div>
                <div className="text-sm font-semibold text-slate-200 mt-0.5">FastAPI & Next.js</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Execution</div>
                <div className="text-sm font-semibold text-slate-200 mt-0.5">Alpaca Paper API</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Integrity</div>
                <div className="text-sm font-semibold text-slate-200 mt-0.5">PostgreSQL Locks</div>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive FinTech Analytics Visual */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl border border-slate-800/90 bg-gradient-to-b from-slate-900/90 to-[#0c121e]/90 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
              {/* Demo Badge */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
                <div className="flex items-center gap-2.5">
                  <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center font-bold text-emerald-400 text-sm">
                    AAPL
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Apple Inc.</div>
                    <div className="text-xs text-slate-400">NASDAQ · Technology</div>
                  </div>
                </div>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono font-medium text-amber-400 border border-amber-500/20">
                  DEMO DATA
                </span>
              </div>

              {/* Price & Change Header */}
              <div className="mt-4 flex items-baseline justify-between">
                <div>
                  <div className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-tight">
                    $189.45
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400 mt-0.5">
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                    <span className="font-semibold">+3.85 (+2.07%)</span>
                    <span className="text-slate-400 font-normal">Past Month</span>
                  </div>
                </div>

                {/* Range Selector */}
                <div className="flex gap-1 bg-slate-950/70 p-1 rounded-lg border border-slate-800 text-[11px] font-medium text-slate-400">
                  {(['1D', '1W', '1M', '1Y'] as const).map((range) => (
                    <button
                      key={range}
                      type="button"
                      onClick={() => setSelectedRange(range)}
                      className={`px-2 py-0.5 rounded transition ${
                        selectedRange === range
                          ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30'
                          : 'hover:text-slate-200'
                      }`}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chart Visual (SVG with gradient fill & smooth spline) */}
              <div className="relative mt-5 h-44 w-full">
                {/* Chart Grid Lines */}
                <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
                  <div className="border-b border-dashed border-slate-600 w-full" />
                  <div className="border-b border-dashed border-slate-600 w-full" />
                  <div className="border-b border-dashed border-slate-600 w-full" />
                  <div className="border-b border-dashed border-slate-600 w-full" />
                </div>

                <svg className="h-full w-full overflow-visible" viewBox="0 0 400 150" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Fill Area */}
                  <path
                    d="M0,130 C40,120 70,135 110,105 C150,75 180,95 220,65 C260,35 300,50 340,30 C370,18 390,22 400,15 L400,150 L0,150 Z"
                    fill="url(#chartGradient)"
                  />
                  {/* Stroke Line */}
                  <path
                    d="M0,130 C40,120 70,135 110,105 C150,75 180,95 220,65 C260,35 300,50 340,30 C370,18 390,22 400,15"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Glowing end point */}
                  <circle cx="400" cy="15" r="4.5" fill="#10b981" />
                  <circle cx="400" cy="15" r="9" fill="#10b981" opacity="0.3" className="animate-ping" />
                </svg>
              </div>

              {/* Model Prediction & Trading Signal Stack */}
              <div className="mt-5 space-y-2.5">
                {/* Prediction Bar */}
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                    <span className="text-slate-300 font-medium">Model Forecast:</span>
                    <span className="font-mono text-emerald-400 font-semibold">+2.4% Probability</span>
                  </div>
                  <span className="font-mono text-slate-400">Conf: 74.2%</span>
                </div>

                {/* Signal Card */}
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-emerald-500 px-2 py-0.5 text-[11px] font-bold text-slate-950">
                      BUY
                    </span>
                    <span className="text-slate-200">Signal Score: <strong className="font-mono text-emerald-300">0.742</strong></span>
                  </div>
                  <span className="text-slate-400 text-[11px]">Sentiment + Momentum</span>
                </div>
              </div>

              {/* Data Disclaimer */}
              <div className="mt-3 text-center text-[10px] text-slate-400 font-mono">
                Illustrative sample chart data · Not real-time financial advice
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
