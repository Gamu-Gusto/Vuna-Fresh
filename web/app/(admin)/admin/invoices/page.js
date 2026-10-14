'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

const STATUSES = [
  { value: 'pending', label: 'Pending' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'paid', label: 'Paid' },
  { value: 'written_off', label: 'Written off' },
];

// Business-buyer invoices (credit terms). Buyers pay by EFT with INV-<id> as the
// reference; admin checks the bank statement and updates the status here.
export default function AdminInvoicesPage() {
  const [filter, setFilter] = useState('');
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get(`/invoices/${filter ? `?status=${filter}` : ''}`)
      .then(data => setInvoices(data.results ?? data))
      .catch(() => setError('Could not load invoices.'))
      .finally(() => setLoading(false));
  }, [filter]);

  async function setStatus(invoice, status) {
    setError('');
    try {
      const updated = await apiClient.patch(`/invoices/${invoice.id}/`, { status });
      setInvoices(is => is.map(i => (i.id === invoice.id ? { ...i, ...updated } : i)));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Match EFT payments by reference (INV-number), then mark the invoice paid.</p>
        </div>
        <select value={filter} onChange={e => { setLoading(true); setFilter(e.target.value); }} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white">
          <option value="">All</option>
          {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>}

      {loading ? (
        <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>
      ) : invoices.length === 0 ? (
        <div className="text-gray-600">No invoices.</div>
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-gray-500">
              <tr>
                <th className="px-4 py-3">Reference</th>
                <th className="px-4 py-3">Buyer</th>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Due</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {invoices.map(i => (
                <tr key={i.id}>
                  <td className="px-4 py-3 font-mono">INV-{i.id}</td>
                  <td className="px-4 py-3 text-gray-600">{i.buyer_email}</td>
                  <td className="px-4 py-3"><Link href={`/admin/orders/${i.order}`} className="font-mono text-brand-green hover:underline">#{i.order}</Link></td>
                  <td className="px-4 py-3 text-gray-600">{new Date(i.due_date).toLocaleDateString('en-ZA')}</td>
                  <td className="px-4 py-3 font-mono">R{Number(i.amount).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <select value={i.status} onChange={e => setStatus(i, e.target.value)} className="border border-gray-300 rounded-lg px-2 py-1 text-xs bg-white">
                      {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
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
