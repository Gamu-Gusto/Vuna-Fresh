'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

// Farmer payouts are calculated when a buyer payment is confirmed, but a farm
// is paid only once the driver has confirmed the order was delivered. Admin
// pays each farm by EFT outside the system, then marks the payout paid here.
export default function AdminPayoutsPage() {
  const { user } = useAuth();
  // Paying farmers is reserved for the super admin; managers see the same list
  const canPay = Boolean(user?.is_super_admin);
  const [status, setStatus] = useState('pending');
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    apiClient.get(`/payments/payouts/${status ? `?status=${status}` : ''}`)
      .then(data => setPayouts(data.results ?? data))
      .catch(() => setError('Could not load payouts.'))
      .finally(() => setLoading(false));
  }, [status]);

  async function markPaid(p) {
    if (!window.confirm(`Confirm you've paid ${p.farm_name} R${Number(p.net_amount).toFixed(2)} for order #${p.order_id}?`)) return;
    setError('');
    setBusy(p.id);
    try {
      const updated = await apiClient.post(`/payments/payouts/${p.id}/mark_paid/`);
      setPayouts(ps => (status === 'pending' ? ps.filter(x => x.id !== p.id) : ps.map(x => (x.id === p.id ? updated : x))));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  const ready = payouts.filter(p => p.ready_to_pay);
  const total = ready.reduce((s, p) => s + Number(p.net_amount), 0);
  const waiting = payouts.filter(p => p.status === 'pending' && !p.ready_to_pay).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Farmer payouts</h1>
          <p className="text-sm text-gray-500 mt-1">
            {canPay
              ? 'Once an order is delivered, pay each farm by EFT, then mark the payout as paid.'
              : 'Only the super admin can pay farmers. You can see what is due and when.'}
          </p>
        </div>
        <select value={status} onChange={e => { setLoading(true); setStatus(e.target.value); }} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white">
          <option value="pending">Pending</option>
          <option value="paid">Paid</option>
          <option value="">All</option>
        </select>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>}

      {loading ? (
        <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>
      ) : payouts.length === 0 ? (
        <div className="text-gray-600">No payouts in this list.</div>
      ) : (
        <>
          {status === 'pending' && (
            <p className="text-sm text-gray-600">
              {canPay ? 'Ready to pay now' : 'Due now'}: <span className="font-mono font-semibold">R{total.toFixed(2)}</span>
              {waiting > 0 && <span className="text-gray-400"> · {waiting} awaiting delivery</span>}
            </p>
          )}
          <div className="bg-white rounded border border-hairline overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs font-semibold text-gray-500">
                <tr>
                  <th className="px-4 py-3">Farm</th>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Gross</th>
                  <th className="px-4 py-3">Commission</th>
                  <th className="px-4 py-3">Pay farm</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {payouts.map(p => (
                  <tr key={p.id}>
                    <td className="px-4 py-3 font-medium text-gray-800">{p.farm_name}</td>
                    <td className="px-4 py-3"><Link href={`/admin/orders/${p.order_id}`} className="font-mono text-brand-green hover:underline">#{p.order_id}</Link></td>
                    <td className="px-4 py-3 font-mono">R{Number(p.gross_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-gray-500">R{Number(p.commission_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono font-semibold">R{Number(p.net_amount).toFixed(2)}</td>
                    <td className="px-4 py-3 text-right">
                      {p.ready_to_pay && canPay ? (
                        <button onClick={() => markPaid(p)} disabled={busy === p.id} className="btn-primary text-xs px-3 py-1.5 disabled:opacity-60">Mark paid</button>
                      ) : p.status === 'pending' ? (
                        <span className="text-xs text-gray-400">
                          {p.order_status === 'cancelled' ? 'Order cancelled' : p.ready_to_pay ? 'Ready for the super admin' : 'Awaiting delivery'}
                        </span>
                      ) : (
                        <span className="text-xs text-brand-green">Paid {p.paid_at && new Date(p.paid_at).toLocaleDateString('en-ZA')}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
