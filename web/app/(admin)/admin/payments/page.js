'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

// Proof-of-payment review for EFT / direct deposit orders. Approving marks the
// order paid (and calculates farmer payouts); rejecting fails the transaction
// and notifies the buyer, who can then pay again with a fresh reference.
export default function AdminPaymentsPage() {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [rejectState, setRejectState] = useState(null); // { id, notes }
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    apiClient.get('/payments/deposit-proofs/pending/')
      .then(data => setProofs(data.results ?? data))
      .catch(() => setError('Could not load payments awaiting review.'))
      .finally(() => setLoading(false));
  }, []);

  async function review(id, body) {
    setActionError('');
    setActionLoading(true);
    try {
      await apiClient.post(`/payments/deposit-proofs/${id}/review/`, body);
      setProofs(ps => ps.filter(p => p.id !== id));
      setRejectState(null);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Payments to verify</h1>
        <p className="text-sm text-gray-500 mt-1">
          Check each payment has arrived in the bank account with the matching reference before approving.
        </p>
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{actionError}</div>
      )}

      {proofs.length === 0 ? (
        <div className="text-gray-600">
          No payments are waiting to be checked.
        </div>
      ) : (
        <div className="space-y-3">
          {proofs.map(p => {
            const refMismatch = p.bank_reference_number.trim().toUpperCase() !== (p.expected_reference ?? '').toUpperCase();
            const rejecting = rejectState?.id === p.id;
            return (
              <div key={p.id} className="bg-white rounded border border-hairline p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 space-y-1">
                    <p className="font-semibold text-gray-900">
                      <Link href={`/admin/orders/${p.order_id}`} className="hover:underline font-mono">Order #{p.order_id}</Link>
                      <span className="ml-3 text-brand-green font-mono">R{Number(p.amount).toFixed(2)}</span>
                    </p>
                    <p className="text-sm text-gray-500">{p.uploaded_by_email}</p>
                    <p className="text-sm text-gray-600">
                      Expected reference: <span className="font-mono">{p.expected_reference}</span>
                      {', '}buyer used: <span className={`font-mono ${refMismatch ? 'text-amber-700 font-semibold' : ''}`}>{p.bank_reference_number}</span>
                      {refMismatch && <span className="ml-1 text-xs text-amber-700">(doesn&apos;t match)</span>}
                    </p>
                    <p className="text-xs text-gray-400">Submitted {new Date(p.created_at).toLocaleString('en-ZA')}</p>
                    <a href={p.file_url} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-brand-green font-medium hover:underline">
                      View proof of payment ↗
                    </a>
                  </div>

                  {!rejecting && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => review(p.id, { action: 'approve' })}
                        disabled={actionLoading}
                        className="btn-primary text-sm px-4 py-1.5 disabled:opacity-60"
                      >
                        Mark as paid
                      </button>
                      <button
                        onClick={() => setRejectState({ id: p.id, notes: '' })}
                        disabled={actionLoading}
                        className="bg-white text-red-600 border border-red-200 text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-60"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>

                {rejecting && (
                  <div className="mt-4 border-t border-hairline pt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Reason (sent to the buyer) <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={rejectState.notes}
                      onChange={e => setRejectState(s => ({ ...s, notes: e.target.value }))}
                      rows={2}
                      placeholder="e.g. Payment not received in the account yet"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
                    />
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={() => review(p.id, { action: 'reject', notes: rejectState.notes.trim() })}
                        disabled={actionLoading || !rejectState.notes.trim()}
                        className="bg-red-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-60"
                      >
                        {actionLoading ? 'Rejecting…' : 'Confirm reject'}
                      </button>
                      <button
                        onClick={() => setRejectState(null)}
                        disabled={actionLoading}
                        className="text-sm text-gray-500 hover:text-gray-700 px-4 py-1.5"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
