'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import RequireLogin from '@/components/RequireLogin';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';

const FREQUENCY_LABELS = { weekly: 'Every week', biweekly: 'Every 2 weeks', monthly: 'Every month' };
const STATUS_TEXT = { active: 'text-brand-green', paused: 'text-amber-700', cancelled: 'text-gray-400' };

export default function SubscriptionsPage() {
  return (
    <RequireLogin message="Please log in to manage your subscriptions.">
      <Subscriptions />
    </RequireLogin>
  );
}

function Subscriptions() {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    apiClient.get('/subscriptions/')
      .then(data => setSubs(data.results ?? data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function act(id, action) {
    if (action === 'cancel' && !window.confirm('Cancel this subscription? You can subscribe again from the product page.')) return;
    setActionError('');
    setBusy(id);
    try {
      const updated = await apiClient.post(`/subscriptions/${id}/${action}/`);
      setSubs(ss => ss.map(s => (s.id === id ? updated : s)));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Subscriptions</h1>
        <p className="text-sm text-gray-500 mt-1">
          Regular deliveries of your favourites. Each delivery becomes an order you pay for by EFT as usual.
        </p>
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{actionError}</div>
      )}

      {subs.length === 0 ? (
        <EmptyState className="py-12">
          <span className="block mb-3">No subscriptions yet. Subscribe from any product page.</span>
          <Link href="/products" className="text-brand-green font-medium hover:underline">Browse products</Link>
        </EmptyState>
      ) : (
        <ul className="space-y-3">
          {subs.map(s => (
            <li key={s.id} className="bg-white rounded border border-hairline p-4 flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm">
                <Link href={`/products/${s.product}`} className="font-semibold text-gray-800 hover:underline">{s.product_name}</Link>
                <p className="text-gray-600">
                  <span className="font-mono">{s.quantity}</span> × {s.product_unit}, {(FREQUENCY_LABELS[s.frequency] ?? s.frequency).toLowerCase()}
                  {', '}<span className="font-mono">R{(Number(s.product_price) * s.quantity).toFixed(2)}</span>
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  <span className={`font-semibold capitalize ${STATUS_TEXT[s.status] ?? ''}`}>{s.status}</span>
                  {s.status === 'active' && <>. Next delivery {new Date(s.next_delivery_date).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })}</>}
                </p>
              </div>
              {s.status !== 'cancelled' && (
                <div className="flex gap-2">
                  {s.status === 'active' ? (
                    <button onClick={() => act(s.id, 'pause')} disabled={busy === s.id} className="text-sm font-semibold px-3 py-1.5 rounded-lg border border-hairline text-gray-700 hover:bg-gray-50 disabled:opacity-60">Pause</button>
                  ) : (
                    <button onClick={() => act(s.id, 'resume')} disabled={busy === s.id} className="text-sm font-semibold px-3 py-1.5 rounded-lg btn-primary disabled:opacity-60">Resume</button>
                  )}
                  <button onClick={() => act(s.id, 'cancel')} disabled={busy === s.id} className="text-sm font-semibold px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-60">Cancel</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
