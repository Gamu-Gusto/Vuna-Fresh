'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import RequireLogin from '@/components/RequireLogin';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';
import BankDetails from '@/components/BankDetails';

const STATUS_STYLE = {
  pending: 'text-amber-700',
  overdue: 'text-ember font-semibold',
  paid: 'text-brand-green',
  written_off: 'text-gray-400',
};

// Business buyers on credit terms are invoiced when an order is delivered,
// and pay each invoice by EFT using INV-<id> as the reference.
export default function InvoicesPage() {
  return (
    <RequireLogin message="Please log in to see your invoices.">
      <Invoices />
    </RequireLogin>
  );
}

function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [bank, setBank] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([apiClient.get('/invoices/'), apiClient.get('/payments/bank-details/')])
      .then(([inv, b]) => {
        setInvoices(inv.results ?? inv);
        setBank(b);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  const outstanding = invoices.filter(i => i.status === 'pending' || i.status === 'overdue');
  const totalDue = outstanding.reduce((sum, i) => sum + Number(i.amount), 0);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Invoices</h1>
        <p className="text-sm text-gray-500 mt-1">For business accounts on credit terms. Orders are invoiced on delivery.</p>
      </div>

      {invoices.length === 0 ? (
        <EmptyState className="py-12">No invoices yet.</EmptyState>
      ) : (
        <>
          {outstanding.length > 0 && bank && (
            <div className="bg-white rounded border border-hairline p-4">
              <h2 className="font-semibold text-gray-700">
                Outstanding: <span className="font-mono text-brand-green">R{totalDue.toFixed(2)}</span>
              </h2>
              <p className="text-sm text-gray-500 mb-2">Pay each invoice by EFT, using its invoice number as the reference.</p>
              <BankDetails details={bank} />
            </div>
          )}

          <div className="bg-white rounded border border-hairline overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs font-semibold text-gray-500">
                <tr>
                  <th className="px-4 py-3">Invoice / reference</th>
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
                    <td className="px-4 py-3 font-mono text-gray-600">#{i.order}</td>
                    <td className="px-4 py-3 text-gray-600">{new Date(i.due_date).toLocaleDateString('en-ZA')}</td>
                    <td className="px-4 py-3 font-mono">R{Number(i.amount).toFixed(2)}</td>
                    <td className={`px-4 py-3 capitalize ${STATUS_STYLE[i.status] ?? ''}`}>{i.status.replace('_', ' ')}</td>
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
