'use client';

import React from 'react';

interface TickerData {
  symbol: string;
  name: string;
  price: string;
  change: string;
  isPositive: boolean;
  score: string;
  signal: 'BUY' | 'HOLD' | 'SELL';
  sparkPath: string;
}

const SAMPLE_TICKERS: TickerData[] = [
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    price: '$189.45',
    change: '+2.07%',
    isPositive: true,
    score: '0.742',
    signal: 'BUY',
    sparkPath: 'M0,25 Q20,28 40,18 T80,12 T120,4',
  },
  {
    symbol: 'MSFT',
    name: 'Microsoft Corp.',
    price: '$425.20',
    change: '+0.85%',
    isPositive: true,
    score: '0.518',
    signal: 'HOLD',
    sparkPath: 'M0,20 Q20,15 40,22 T80,18 T120,14',
  },
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corp.',
    price: '$132.80',
    change: '+3.41%',
    isPositive: true,
    score: '0.812',
    signal: 'BUY',
    sparkPath: 'M0,28 Q20,22 40,26 T80,10 T120,2',
  },
];

export function MarketOverview() {
  return (
    <section className="relative py-12 border-y border-slate-800/80 bg-slate-950/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Coverage Watchlist
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white mt-1">
              Active Strategy Universe
            </h2>
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-mono text-amber-300">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
            <span>SAMPLE DEMO DATA · RECENT MODEL RUNS</span>
          </div>
        </div>

        {/* Ticker Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SAMPLE_TICKERS.map((item) => (
            <div
              key={item.symbol}
              className="group relative rounded-xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-5 hover:border-slate-700 hover:shadow-lg hover:shadow-emerald-950/20 transition-all duration-300"
            >
              {/* Card Top */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-white tracking-tight">{item.symbol}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-bold ${
                        item.signal === 'BUY'
                          ? 'bg-emerald-500 text-slate-950'
                          : item.signal === 'SELL'
                          ? 'bg-rose-500 text-white'
                          : 'bg-slate-700 text-slate-200'
                      }`}
                    >
                      {item.signal}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">{item.name}</div>
                </div>

                {/* Sparkline */}
                <div className="h-8 w-28">
                  <svg className="h-full w-full overflow-visible" viewBox="0 0 120 30">
                    <path
                      d={item.sparkPath}
                      fill="none"
                      stroke={item.isPositive ? '#10b981' : '#f43f5e'}
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              </div>

              {/* Price & Change */}
              <div className="mt-5 flex items-baseline justify-between border-t border-slate-800/80 pt-4">
                <div>
                  <div className="text-xs text-slate-400">Reference Price</div>
                  <div className="text-lg font-mono font-semibold text-white mt-0.5">{item.price}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">Day Change</div>
                  <div className="text-sm font-mono font-medium text-emerald-400 mt-0.5">
                    {item.change}
                  </div>
                </div>
              </div>

              {/* Prediction Score Bar */}
              <div className="mt-4 rounded-lg bg-slate-950/80 border border-slate-800/60 p-2.5 flex items-center justify-between text-xs">
                <span className="text-slate-400">ML Model Score</span>
                <span className="font-mono font-semibold text-emerald-300">{item.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
