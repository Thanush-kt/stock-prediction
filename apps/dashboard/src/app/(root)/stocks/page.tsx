'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import type { Ticker } from '@/types/api';

export default function StocksOverviewPage() {
  const [stocks, setStocks] = useState<Ticker[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedExchange, setSelectedExchange] = useState<string>('all');

  useEffect(() => {
    let mounted = true;
    api
      .stocks()
      .then((data) => {
        if (mounted) {
          setStocks(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const filteredStocks = useMemo(() => {
    const q = search.trim().toUpperCase();
    return stocks.filter((s) => {
      if (q && !s.symbol.toUpperCase().includes(q) && !(s.name && s.name.toUpperCase().includes(q))) {
        return false;
      }
      if (selectedExchange !== 'all') {
        if (selectedExchange === 'NSE' && s.exchange !== 'NSE') return false;
        if (selectedExchange === 'US' && s.exchange !== 'NYSE') return false;
        if (selectedExchange === 'crypto' && s.asset_class !== 'crypto') return false;
        if (selectedExchange === 'commodity' && s.asset_class !== 'commodity') return false;
      }
      return true;
    });
  }, [stocks, search, selectedExchange]);

  const getExchangeBadge = (exchange: string, assetClass: string) => {
    if (exchange === 'NSE') {
      return (
        <span className="inline-flex items-center rounded-md bg-orange-500/10 px-2.5 py-1 text-xs font-semibold text-orange-400 border border-orange-500/20">
          🇮🇳 NSE India
        </span>
      );
    }
    if (assetClass === 'crypto') {
      return (
        <span className="inline-flex items-center rounded-md bg-purple-500/10 px-2.5 py-1 text-xs font-semibold text-purple-400 border border-purple-500/20">
          🪙 Crypto Asset
        </span>
      );
    }
    if (assetClass === 'commodity') {
      return (
        <span className="inline-flex items-center rounded-md bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20">
          📦 Commodity
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-md bg-blue-500/10 px-2.5 py-1 text-xs font-semibold text-blue-400 border border-blue-500/20">
        🇺🇸 US Equity
      </span>
    );
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
            Asset Universe
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Tracked Assets & Equities
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Multi-exchange coverage across US equities, Indian NSE markets, cryptocurrencies, and commodity futures.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            {stocks.length} Registered Symbols
          </span>
        </div>
      </div>

      {/* Search & Exchange Filter Bar */}
      <div className="rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-4 shadow-xl backdrop-blur-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <svg
            className="absolute left-3.5 top-3 h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by symbol or name (e.g. AAPL, RELIANCE.NS, BTC)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-800 bg-slate-900/90 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 p-1 text-xs font-medium">
          {[
            { id: 'all', label: 'All Markets' },
            { id: 'US', label: 'US Equities' },
            { id: 'NSE', label: 'NSE India' },
            { id: 'crypto', label: 'Crypto' },
            { id: 'commodity', label: 'Commodities' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSelectedExchange(tab.id)}
              className={`rounded-lg px-3 py-1.5 transition ${
                selectedExchange === tab.id
                  ? 'bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Assets Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 animate-pulse">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-40 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-3">
              <div className="h-5 w-24 bg-slate-800 rounded"></div>
              <div className="h-4 w-40 bg-slate-800/60 rounded"></div>
              <div className="h-8 w-full bg-slate-800/30 rounded"></div>
            </div>
          ))}
        </div>
      ) : filteredStocks.length === 0 ? (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-12 text-center space-y-3">
          <div className="text-base font-semibold text-slate-300">No assets matching filters</div>
          <p className="text-xs text-slate-400">
            Ingest new market data symbols using <code className="text-emerald-400">stockpred ingest-prices</code>.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredStocks.map((stock) => (
            <Link
              key={stock.symbol}
              href={`/stocks/${encodeURIComponent(stock.symbol)}`}
              className="group rounded-2xl border border-slate-800/80 bg-[#0c121d]/70 p-6 shadow-xl backdrop-blur-xl transition-all duration-300 hover:border-emerald-500/50 hover:bg-[#101827] hover:shadow-[0_0_25px_rgba(16,185,129,0.1)] flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold font-mono text-white group-hover:text-emerald-400 transition-colors">
                    {stock.symbol}
                  </span>
                  {getExchangeBadge(stock.exchange, stock.asset_class)}
                </div>
                <div className="mt-1 text-xs text-slate-400 font-medium truncate">
                  {stock.name || 'Financial Asset'}
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-slate-800/60 pt-4 text-xs">
                <span className="text-slate-400 capitalize">
                  Asset Class: <span className="text-slate-300 font-medium">{stock.asset_class}</span>
                </span>
                <span className="text-emerald-400 font-semibold group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                  Analytics →
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
