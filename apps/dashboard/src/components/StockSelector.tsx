'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { Ticker } from '@/types/api';
import { api } from '@/lib/api';

interface StockSelectorProps {
  selectedSymbol: string | null;
  onSelect: (symbol: string) => void;
  className?: string;
}

export function StockSelector({ selectedSymbol, onSelect, className = '' }: StockSelectorProps) {
  const [stocks, setStocks] = useState<Ticker[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase();
    if (!q) return stocks;
    return stocks.filter(
      (s) => s.symbol.toUpperCase().includes(q) || (s.name && s.name.toUpperCase().includes(q))
    );
  }, [stocks, search]);

  const selectedTicker = useMemo(
    () => stocks.find((s) => s.symbol === selectedSymbol),
    [stocks, selectedSymbol]
  );

  const getExchangeBadge = (exchange: string, assetClass: string) => {
    if (exchange === 'NSE') {
      return (
        <span className="inline-flex items-center rounded-md bg-orange-500/10 px-2 py-0.5 text-xs font-semibold text-orange-400 border border-orange-500/20">
          🇮🇳 NSE
        </span>
      );
    }
    if (assetClass === 'crypto') {
      return (
        <span className="inline-flex items-center rounded-md bg-purple-500/10 px-2 py-0.5 text-xs font-semibold text-purple-400 border border-purple-500/20">
          🪙 Crypto
        </span>
      );
    }
    if (assetClass === 'commodity') {
      return (
        <span className="inline-flex items-center rounded-md bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">
          📦 Commodity
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-md bg-blue-500/10 px-2 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/20">
        🇺🇸 US Eq
      </span>
    );
  };

  return (
    <div ref={containerRef} className={`relative w-full max-w-sm ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex h-11 w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900/80 px-3.5 py-2 text-sm text-slate-100 shadow-inner backdrop-blur-md transition hover:border-slate-700 hover:bg-slate-800/80 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      >
        <div className="flex items-center gap-2.5 truncate">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          {selectedTicker ? (
            <div className="flex items-center gap-2 truncate">
              <span className="font-bold tracking-tight text-white">{selectedTicker.symbol}</span>
              {selectedTicker.name && (
                <span className="text-xs text-slate-400 truncate max-w-[120px]">{selectedTicker.name}</span>
              )}
              {getExchangeBadge(selectedTicker.exchange, selectedTicker.asset_class)}
            </div>
          ) : (
            <span className="text-slate-400">
              {loading ? 'Loading symbols...' : 'Select a stock or asset...'}
            </span>
          )}
        </div>
        <svg
          className={`h-4 w-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-2 w-full rounded-2xl border border-slate-800 bg-[#0d131f]/95 p-2 shadow-2xl backdrop-blur-xl transition-all">
          <div className="relative mb-2">
            <svg
              className="absolute left-3 top-2.5 h-4 w-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              autoFocus
              placeholder="Search ticker or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
            />
          </div>

          <div className="max-h-60 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
            {filtered.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-500">
                No matching symbols found.
              </div>
            ) : (
              filtered.map((stock) => {
                const isSelected = stock.symbol === selectedSymbol;
                return (
                  <button
                    key={stock.symbol}
                    type="button"
                    onClick={() => {
                      onSelect(stock.symbol);
                      setIsOpen(false);
                      setSearch('');
                    }}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-xs transition ${
                      isSelected
                        ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`}
                  >
                    <div className="flex flex-col">
                      <span className="font-bold font-mono tracking-tight text-white">{stock.symbol}</span>
                      {stock.name && <span className="text-[11px] text-slate-400 truncate max-w-[170px]">{stock.name}</span>}
                    </div>
                    <div>{getExchangeBadge(stock.exchange, stock.asset_class)}</div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
