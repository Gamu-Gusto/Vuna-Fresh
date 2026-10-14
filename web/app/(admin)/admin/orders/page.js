'use client';

import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '@/lib/api';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import PaymentStatusBadge from '@/components/PaymentStatusBadge';
import EmptyState from '@/components/EmptyState';

const ALL_STATUSES = ['placed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'cancelled'];

const STATUS_LABELS = {
  placed: 'Placed',
  preparing: 'Preparing',
  ready_for_pickup: 'Ready for pickup',
  out_for_delivery: 'Out for delivery',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
};

export default function AdminOrdersPage() {
  const [allOrders, setAllOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Backend has no status filter on the orders endpoint, so fetch all and filter client-side.
    // page_size=100 is sufficient for Phase 1 volume.
    apiClient.get('/orders/?page_size=100')
      .then(data => setAllOrders(data.results ?? []))
      .catch(() => setError('Could not load orders.'))
      .finally(() => setLoading(false));
  }, []);

  const orders = useMemo(
    () => statusFilter ? allOrders.filter(o => o.status === statusFilter) : allOrders,
    [allOrders, statusFilter]
  );

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
          <p className="text-sm text-gray-500 mt-1">
            {orders.length} of {allOrders.length} orders
          </p>
        </div>

        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green"
        >
          <option value="">All statuses</option>
          {ALL_STATUSES.map(s => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>
      </div>

      {orders.length === 0 ? (
        <EmptyState className="p-12">
          {statusFilter ? `No orders with status "${STATUS_LABELS[statusFilter]}".` : 'No orders yet.'}
        </EmptyState>
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hairline text-left text-xs font-semibold text-gray-500">
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Buyer</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {orders.map(order => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900 font-mono">#{order.id}</td>
                  <td className="px-4 py-3 text-gray-600">{order.buyer_email}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(order.created_at).toLocaleDateString('en-ZA')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <OrderStatusBadge status={order.status} />
                      <PaymentStatusBadge status={order.payment?.status} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-700 font-medium font-mono">
                    R{Number(order.total).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/admin/orders/${order.id}`}
                      className="text-brand-green hover:underline text-xs font-medium"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
