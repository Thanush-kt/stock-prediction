import React from 'react';

export function AboutSection() {
  return (
    <section id="about" className="py-20 lg:py-28 border-t border-slate-800/80 bg-slate-950/40 relative">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Text */}
          <div className="lg:col-span-7 space-y-6">
            <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Platform Philosophy
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white leading-tight">
              Grounded In Transparency, Not Empty Claims
            </h2>
            <p className="text-slate-300 text-base leading-relaxed">
              Stock-Prediction brings together machine learning, financial data analysis, trading signals, and paper trading in one platform.
            </p>
            <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
              Rather than promoting black-box magic or speculative shortcuts, our mission is to provide an open, verifiable testbed where algorithmic hypotheses can be formulated, backtested, and simulated under strict risk constraints before any capital is committed.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4">
              <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
                <div className="text-emerald-400 font-bold text-sm">Empirical Rigor</div>
                <div className="text-slate-400 text-xs mt-1">
                  Feature pipelines, confidence distributions, and explicit rationale breakdowns for every signal.
                </div>
              </div>
              <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
                <div className="text-emerald-400 font-bold text-sm">Execution Safety</div>
                <div className="text-slate-400 text-xs mt-1">
                  PostgreSQL advisory locking and idempotent signal indices ensure duplicate orders are prevented.
                </div>
              </div>
            </div>
          </div>

          {/* Right Highlights Panel */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/80 to-[#0c121e] p-6 lg:p-8 space-y-5">
              <h3 className="text-lg font-semibold text-white tracking-tight">
                Analytical Safeguards
              </h3>

              <div className="space-y-4 text-xs">
                <div className="flex gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    ✓
                  </div>
                  <div>
                    <div className="font-semibold text-slate-200">Zero Real Capital Exposure</div>
                    <div className="text-slate-400 mt-0.5">Executes strictly within Alpaca paper-trading sandbox endpoints.</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    ✓
                  </div>
                  <div>
                    <div className="font-semibold text-slate-200">Clerk Enterprise Authentication</div>
                    <div className="text-slate-400 mt-0.5">Secures sensitive strategy endpoints with RS256 JWKS session verification.</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    ✓
                  </div>
                  <div>
                    <div className="font-semibold text-slate-200">Exposure Cap Protection</div>
                    <div className="text-slate-400 mt-0.5">Automated circuit breakers halt execution if drawdown or risk thresholds trigger.</div>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                Educational and research software built for developers, quantitative traders, and data scientists.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
