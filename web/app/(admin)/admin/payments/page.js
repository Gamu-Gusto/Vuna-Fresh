'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient, openPrivateFile } from '@/lib/api';

// Payment review for EFT / direct deposit orders. The buyer's uploaded proof is
// only a notice: an order is marked paid (releasing it to the farmers and
// calculating payouts) only when an admin confirms the money has cleared in
// the Vuna Fresh bank account and records what the bank statement shows.
// Rejecting fails the transaction and notifies the buyer, who can then pay
// again with a fresh reference.

const EMPTY_CONFIRM = { amount_received: '', received_on: '', bank_statement_reference: '', funds_cleared: false };

function errorText(err) {
  if (!err.detail || typeof err.detail !== 'object') return err.message;
  return Object.values(err.detail).flat().join(' ');
}

export default function AdminPaymentsPage() {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [rejectState, setRejectState] = useState(null); // { id, notes }
  const [confirmState, setConfirmState] = useState(null); // { id, ...EMPTY_CONFIRM }
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
      setConfirmState(null);
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setActionLoading(false);
    }
  }

  function openConfirm(id) {
    setActionError('');
    setRejectState(null);
    setConfirmState({ id, ...EMPTY_CONFIRM });
  }

  function openReject(id) {
    setActionError('');
    setConfirmState(null);
    setRejectState({ id, notes: '' });
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  const today = new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD in local time

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Payments to verify</h1>
        <p className="text-sm text-gray-500 mt-1">
          A proof of payment is not payment. Open the Vuna Fresh bank account and find the deposit before confirming.
          The order only goes to the farmers once you confirm the funds have cleared.
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
            const confirming = confirmState?.id === p.id;
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
                    {p.has_file ? (
                      <button
                        type="button"
                        onClick={() => openPrivateFile(`/payments/deposit-proofs/${p.id}/file/`).catch(err => setActionError(err.message))}
                        className="inline-block text-sm text-brand-green font-medium hover:underline"
                      >
                        View proof of payment ↗
                      </button>
                    ) : p.file_url ? (
                      // Proofs uploaded before private storage
                      <a href={p.file_url} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-brand-green font-medium hover:underline">
                        View proof of payment ↗
                      </a>
                    ) : null}
                  </div>

                  {!rejecting && !confirming && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => openConfirm(p.id)}
                        disabled={actionLoading}
                        className="btn-primary text-sm px-4 py-1.5 disabled:opacity-60"
                      >
                        Confirm funds received
                      </button>
                      <button
                        onClick={() => openReject(p.id)}
                        disabled={actionLoading}
                        className="bg-white text-red-600 border border-red-200 text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-60"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>

                {confirming && (
                  <ConfirmFundsForm
                    proof={p}
                    state={confirmState}
                    setState={setConfirmState}
                    today={today}
                    loading={actionLoading}
                    onSubmit={() => {
                      const { id, ...fields } = confirmState;
                      review(id, { action: 'approve', ...fields });
                    }}
                    onCancel={() => setConfirmState(null)}
                  />
                )}

                {rejecting && (
                  <div className="mt-4 border-t border-hairline pt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Reason (sent to the buyer) <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={rejectState.notes}
                      onChange={e => setRejectState(s => ({ ...s, notes: e.target.value }))}
                      rows={2}
                      placeholder="e.g. Payment not received in the account"
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

function ConfirmFundsForm({ proof, state, setState, today, loading, onSubmit, onCancel }) {
  const due = Number(proof.amount);
  const received = state.amount_received === '' ? null : Number(state.amount_received);
  const short = received !== null && received < due;
  const over = received !== null && received > due;
  const refDiffers = state.bank_statement_reference.trim() !== ''
    && state.bank_statement_reference.trim().toUpperCase() !== (proof.expected_reference ?? '').toUpperCase();
  const complete = received !== null && !short && state.received_on && state.bank_statement_reference.trim() && state.funds_cleared;

  function set(name, value) {
    setState(s => ({ ...s, [name]: value }));
  }

  const inputClass = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent';

  return (
    <form
      className="mt-4 border-t border-hairline pt-4 space-y-3"
      onSubmit={e => { e.preventDefault(); if (complete) onSubmit(); }}
    >
      <p className="text-sm text-gray-700">
        Enter what the <strong>Vuna Fresh bank statement</strong> shows for this deposit, not what&apos;s on the proof.
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor={`amount-${proof.id}`} className="block text-sm font-medium text-gray-700 mb-1">Amount received (R)</label>
          <input
            id={`amount-${proof.id}`} type="number" step="0.01" min="0" required
            value={state.amount_received} onChange={e => set('amount_received', e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor={`date-${proof.id}`} className="block text-sm font-medium text-gray-700 mb-1">Date funds arrived</label>
          <input
            id={`date-${proof.id}`} type="date" max={today} required
            value={state.received_on} onChange={e => set('received_on', e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor={`ref-${proof.id}`} className="block text-sm font-medium text-gray-700 mb-1">Reference on statement</label>
          <input
            id={`ref-${proof.id}`} type="text" maxLength={100} required
            value={state.bank_statement_reference} onChange={e => set('bank_statement_reference', e.target.value)}
            className={`${inputClass} font-mono`}
          />
        </div>
      </div>

      {short && (
        <p className="text-sm text-red-600">
          R{received.toFixed(2)} is less than the R{due.toFixed(2)} due. Don&apos;t confirm a short payment: reject it, or wait for the balance.
        </p>
      )}
      {over && (
        <p className="text-sm text-amber-700">
          Overpaid by R{(received - due).toFixed(2)}. You can confirm, but refund the difference to the buyer.
        </p>
      )}
      {refDiffers && (
        <p className="text-sm text-amber-700">
          The statement reference differs from the expected <span className="font-mono">{proof.expected_reference}</span>. Make sure this deposit is really for order #{proof.order_id}.
        </p>
      )}

      <label className="flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox" checked={state.funds_cleared} onChange={e => set('funds_cleared', e.target.checked)}
          className="w-4 h-4 mt-0.5 accent-brand-green"
        />
        <span className="text-sm text-gray-700">
          I have checked the Vuna Fresh bank account, and this money has cleared there. I am not relying on the proof of payment.
        </span>
      </label>

      <div className="flex gap-2">
        <button type="submit" disabled={loading || !complete} className="btn-primary text-sm px-4 py-1.5 disabled:opacity-60">
          {loading ? 'Confirming…' : 'Confirm paid & release order'}
        </button>
        <button type="button" onClick={onCancel} disabled={loading} className="text-sm text-gray-500 hover:text-gray-700 px-4 py-1.5">
          Cancel
        </button>
      </div>
    </form>
  );
}
