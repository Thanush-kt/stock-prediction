'use client';

import React, { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { Order } from '@/types/api';

const STATUS_BADGE: Record<string, string> = {
  filled: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  partially_filled: 'bg-teal-500/20 text-teal-300 border border-teal-500/30',
  pending: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  new: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  accepted: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  rejected: 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
  canceled: 'bg-slate-800 text-slate-400 border border-slate-700',
  cancelled: 'bg-slate-800 text-slate-400 border border-slate-700',
  expired: 'bg-slate-800 text-slate-400 border border-slate-700',
};

function getStatusBadgeClass(status: string): string {
  const normalized = status.toLowerCase();
  return STATUS_BADGE[normalized] ?? 'bg-slate-800 text-slate-400 border border-slate-700';
}

interface OrdersTableProps {
  initialOrders: Order[];
}

export function OrdersTable({ initialOrders }: OrdersTableProps) {
  const [orders, setOrders] = useState<Order[]>(initialOrders);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sideFilter, setSideFilter] = useState('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const availableStatuses = useMemo(() => {
    const set = new Set<string>();
    for (const o of orders) {
      if (o.status) set.add(o.status.toLowerCase());
    }
    return Array.from(set).sort();
  }, [orders]);

  const filteredOrders = useMemo(() => {
    const q = search.trim().toLowerCase();
    return orders.filter((o) => {
      if (q && !o.symbol.toLowerCase().includes(q)) {
        return false;
      }
      if (statusFilter !== 'all' && o.status.toLowerCase() !== statusFilter) {
        return false;
      }
      if (sideFilter !== 'all' && o.side.toLowerCase() !== sideFilter) {
        return false;
      }
      return true;
    });
  }, [orders, search, statusFilter, sideFilter]);

  async function handleRefresh() {
    setIsRefreshing(true);
    setRefreshError(null);
    try {
      const updated = await api.orders({ limit: 100 });
      setOrders(updated);
    } catch {
      setRefreshError('Failed to refresh orders. Check that the API server is reachable.');
    } finally {
      setIsRefreshing(false);
    }
  }

  function handleResetFilters() {
    setSearch('');
    setStatusFilter('all');
    setSideFilter('all');
  }

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-sm">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search ticker (e.g. AAPL)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 pl-9 pr-3 py-2 text-xs font-mono text-white placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition"
            />
          </div>

          {/* Filter Dropdowns & Refresh */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-mono text-slate-300 focus:border-emerald-500 focus:outline-none transition cursor-pointer"
            >
              <option value="all">Status: All</option>
              {availableStatuses.map((st) => (
                <option key={st} value={st}>
                  Status: {st}
                </option>
              ))}
            </select>

            {/* Side Filter */}
            <select
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-mono text-slate-300 focus:border-emerald-500 focus:outline-none transition cursor-pointer"
            >
              <option value="all">Side: All</option>
              <option value="buy">Side: Buy</option>
              <option value="sell">Side: Sell</option>
            </select>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950/80 hover:bg-slate-800/80 px-3.5 py-2 text-xs font-mono font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50 transition cursor-pointer"
            >
              <svg
                className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>

        {refreshError && (
          <div className="text-xs text-rose-400 font-mono bg-rose-950/20 p-2 rounded-lg border border-rose-900/30">
            {refreshError}
          </div>
        )}
      </div>

      {/* Orders Table Container */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 overflow-hidden shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/60 px-5 py-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-white tracking-tight">Order Execution History</h3>
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono font-medium text-emerald-400">
              {filteredOrders.length} {filteredOrders.length === 1 ? 'Order' : 'Orders'}
            </span>
          </div>
          {(search || statusFilter !== 'all' || sideFilter !== 'all') && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-mono text-slate-400 hover:text-white underline cursor-pointer"
            >
              Reset Filters
            </button>
          )}
        </div>

        {filteredOrders.length === 0 ? (
          <div className="p-8 text-center space-y-2">
            <div className="text-sm font-semibold text-slate-300">No matching orders found</div>
            <p className="text-xs text-slate-400">Try adjusting your search criteria or filter selections.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-5">Submitted</th>
                  <th className="py-3 px-5">Symbol</th>
                  <th className="py-3 px-5">Side</th>
                  <th className="py-3 px-5 text-right">Qty</th>
                  <th className="py-3 px-5 text-right">Filled Price</th>
                  <th className="py-3 px-5">Status</th>
                  <th className="py-3 px-5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredOrders.map((o) => {
                  const isExpanded = expandedId === o.id;
                  const sideUpper = o.side.toUpperCase();
                  return (
                    <React.Fragment key={o.id}>
                      <tr className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3.5 px-5 font-mono text-xs text-slate-400">
                          {new Date(o.submitted_at).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-5">
                          <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold font-mono text-xs">
                            {o.symbol}
                          </span>
                        </td>
                        <td className="py-3.5 px-5">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold ${
                              sideUpper === 'BUY'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            }`}
                          >
                            {sideUpper}
                          </span>
                        </td>
                        <td className="py-3.5 px-5 text-right font-mono font-semibold text-slate-200">
                          {o.qty.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-5 text-right font-mono text-slate-300">
                          {o.limit_price ? `$${o.limit_price.toFixed(2)}` : 'Market'}
                        </td>
                        <td className="py-3.5 px-5">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-bold capitalize ${getStatusBadgeClass(o.status)}`}>
                            {o.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-5 text-right">
                          <button
                            type="button"
                            onClick={() => setExpandedId(isExpanded ? null : o.id)}
                            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer transition"
                          >
                            {isExpanded ? 'Hide' : 'Inspect'}
                          </button>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="bg-slate-950/90 px-6 py-4 border-b border-slate-800/80">
                            <div className="rounded-xl border border-slate-800 bg-[#060910] p-4 text-xs font-mono space-y-2">
                              <div className="text-[11px] uppercase tracking-wider text-slate-400">
                                Broker Order Metadata
                              </div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-slate-300 pt-2 border-t border-slate-800/60">
                                <div>
                                  <span className="text-slate-400">Broker Order ID:</span>
                                  <div className="text-white mt-0.5">{o.broker_order_id ?? 'N/A'}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Associated Signal ID:</span>
                                  <div className="text-white mt-0.5">{o.signal_id ?? 'N/A'}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Order Type:</span>
                                  <div className="text-white mt-0.5 uppercase">{o.order_type}</div>
                                </div>
                                <div>
                                  <span className="text-slate-400">Filled Timestamp:</span>
                                  <div className="text-white mt-0.5">{o.filled_at ? new Date(o.filled_at).toLocaleString() : 'Pending'}</div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
