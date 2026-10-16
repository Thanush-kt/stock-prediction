import React from 'react';

const FEATURES = [
  {
    id: 'ml-predictions',
    title: 'Machine Learning Predictions',
    description:
      'Trained predictive models forecast return directions from continuous market indicators, technical momentum, and sentiment data points.',
    badge: 'Quant Models',
    icon: (
      <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'trading-signals',
    title: 'Trading Signals',
    description:
      'The deterministic signal engine tests model confidence against configured strategy rules to output disciplined BUY, SELL, or HOLD decisions.',
    badge: 'Rules Engine',
    icon: (
      <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'risk-management',
    title: 'Risk Management',
    description:
      'Guards against over-concentration through strict exposure limits, drawdown halts, single-trade caps, and PostgreSQL advisory-lock concurrency safeguards.',
    badge: 'Capital Protection',
    icon: (
      <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    id: 'paper-trading',
    title: 'Paper Trading Execution',
    description:
      'Seamless integration with the Alpaca paper-trading sandbox allows simulated order execution and portfolio tracking without real capital risk.',
    badge: 'Alpaca Sandbox',
    icon: (
      <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 18h12l3-18H3zm5 6h8" />
      </svg>
    ),
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-20 lg:py-28 relative">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Core Architecture
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Built for Systematic Strategy Analysis
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Every component is engineered to bridge data ingestion, predictive modeling, and verified broker execution into a coherent workflow.
          </p>
        </div>

        {/* 4 Feature Cards */}
        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-8">
          {FEATURES.map((feat) => (
            <div
              key={feat.id}
              className="group relative rounded-2xl border border-slate-800/80 bg-slate-900/40 p-7 lg:p-8 hover:border-emerald-500/30 hover:bg-slate-900/60 hover:shadow-xl hover:shadow-emerald-950/20 transition-all duration-300"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 group-hover:scale-105 transition-transform duration-300">
                  {feat.icon}
                </div>
                <span className="rounded-full bg-slate-800/80 border border-slate-700/60 px-3 py-1 text-xs font-medium text-slate-300">
                  {feat.badge}
                </span>
              </div>

              <h3 className="mt-5 text-xl font-semibold text-white tracking-tight">
                {feat.title}
              </h3>

              <p className="mt-2.5 text-sm text-slate-400 leading-relaxed">
                {feat.description}
              </p>
            </div>
          ))}
        </div>

        {/* Analytical Note */}
        <div className="mt-10 text-center text-xs text-slate-400">
          All algorithmic components are designed for research, simulation, and hypothesis testing.
        </div>
      </div>
    </section>
  );
}
