import React from 'react';
import { api } from '@/lib/api';
import { OrdersTable } from '@/components/OrdersTable';
import { ErrorMessage } from '@/components/ErrorMessage';
import type { Order } from '@/types/api';

export default async function OrdersPage() {
  let orders: Order[] | null = null;
  let error: string | null = null;

  try {
    orders = await api.orders({ limit: 100 });
  } catch {
    error = 'Could not load order history. Ensure the backend API service is running on port 8000.';
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Simulated Broker Telemetry
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
            Order Execution History
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Submitted, filled, and rejected broker orders tracked in the Alpaca paper-trading sandbox environment.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-300">
            Advisory Lock Protected
          </span>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {orders ? (
        <OrdersTable initialOrders={orders} />
      ) : !error ? (
        <OrdersTable initialOrders={[]} />
      ) : null}
    </div>
  );
}
