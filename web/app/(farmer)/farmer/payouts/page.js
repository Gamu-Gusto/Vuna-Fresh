'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';

// A payout is created for each farm once an order's payment is confirmed:
// the farm's share of the order minus Vuna Fresh's commission. Vuna Fresh
// pays it by EFT and marks it paid.
export default function FarmerPayoutsPage() {
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/payments/payouts/')
      .then(data => setPayouts(data.results ?? data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  const sum = status => payouts.filter(p => p.status === status).reduce((s, p) => s + Number(p.net_amount), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Payouts</h1>
        <p className="text-sm text-gray-500 mt-1">
          Your share of each paid order, after Vuna Fresh&apos;s commission. Payouts are made by EFT to your bank account.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <Stat label="Waiting to be paid" value={sum('pending')} tone="text-amber-700" />
        <Stat label="Paid to you" value={sum('paid')} tone="text-brand-green" />
      </div>

      {payouts.length === 0 ? (
        <EmptyState className="py-12">No payouts yet. They appear here once a buyer&apos;s payment is confirmed.</EmptyState>
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-gray-500">
              <tr>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Sales</th>
                <th className="px-4 py-3">Commission</th>
                <th className="px-4 py-3">You get</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {payouts.map(p => (
                <tr key={p.id}>
                  <td className="px-4 py-3">
                    <Link href={`/farmer/orders/${p.order_id}`} className="font-mono text-brand-green hover:underline">#{p.order_id}</Link>
                    <span className="block text-xs text-gray-400">{new Date(p.created_at).toLocaleDateString('en-ZA')}</span>
                  </td>
                  <td className="px-4 py-3 font-mono">R{Number(p.gross_amount).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">−R{Number(p.commission_amount).toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono font-semibold">R{Number(p.net_amount).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    {p.status === 'paid'
                      ? <span className="text-brand-green">Paid {p.paid_at && new Date(p.paid_at).toLocaleDateString('en-ZA')}</span>
                      : <span className="text-amber-700">Pending</span>}
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

function Stat({ label, value, tone }) {
  return (
    <div className="bg-white rounded border border-hairline p-4">
      <p className="text-xs font-semibold text-gray-500">{label}</p>
      <p className={`text-2xl font-bold font-mono ${tone}`}>R{value.toFixed(2)}</p>
    </div>
  );
}
