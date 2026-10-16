import React from 'react';

const STEPS = [
  {
    step: '01',
    title: 'Market Data',
    subtitle: 'Ingestion & Features',
    description:
      'Continuous collection of historical and real-time market prices, company news feeds, and sentiment indicators normalized into numerical feature tensors.',
  },
  {
    step: '02',
    title: 'ML Analysis',
    subtitle: 'Model Evaluation',
    description:
      'Trained machine learning models process feature inputs to generate forward-looking prediction probabilities and confidence scores for each covered ticker.',
  },
  {
    step: '03',
    title: 'Signal Generation',
    subtitle: 'Strategy & Risk Rules',
    description:
      'Model outputs are evaluated by the strategy engine against strict conviction thresholds, position sizing caps, and concurrency guards to formulate BUY, SELL, or HOLD signals.',
  },
  {
    step: '04',
    title: 'Paper Trading',
    subtitle: 'Simulated Execution',
    description:
      'Validated signals are sent to the Alpaca paper-trading broker sandbox, updating positions, cash balances, and equity curves without financial exposure.',
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 lg:py-28 border-t border-slate-800/80 bg-slate-950/60 relative">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            End-To-End Workflow
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            How The Platform Works
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            A transparent four-stage pipeline transforming raw market telemetry into disciplined, monitored paper trades.
          </p>
        </div>

        {/* Steps Progression: Horizontal on desktop, Vertical on mobile */}
        <div className="mt-16 relative">
          {/* Progression Line (Desktop only) */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 -translate-y-8 h-0.5 bg-gradient-to-r from-emerald-500/20 via-emerald-500/40 to-emerald-500/20 pointer-events-none" />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {STEPS.map((item) => (
              <div
                key={item.step}
                className="relative rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 flex flex-col justify-between hover:border-slate-700 hover:shadow-lg hover:shadow-emerald-950/10 transition-all duration-300"
              >
                <div>
                  {/* Step Number Badge */}
                  <div className="flex items-center justify-between">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/30 font-mono text-base font-bold text-emerald-400 shadow-sm">
                      {item.step}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      Phase {item.step}
                    </span>
                  </div>

                  {/* Title & Subtitle */}
                  <h3 className="mt-5 text-lg font-bold text-white tracking-tight">
                    {item.title}
                  </h3>
                  <div className="text-xs font-medium text-emerald-400/90 mt-0.5">
                    {item.subtitle}
                  </div>

                  {/* Description */}
                  <p className="mt-3 text-xs sm:text-sm text-slate-400 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
