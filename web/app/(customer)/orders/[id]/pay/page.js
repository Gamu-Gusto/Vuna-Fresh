'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { apiClient, uploadFile } from '@/lib/api';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import BankDetails from '@/components/BankDetails';

export default function PayOrderPage() {
  const { id } = useParams();
  const { user, loading: authLoading } = useAuth();

  const [order, setOrder] = useState(null);
  const [payment, setPayment] = useState(null); // bank details + reference from /payments/initiate/
  const [transactionId, setTransactionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [file, setFile] = useState(null);
  const [bankReference, setBankReference] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    if (!user) return;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const o = await apiClient.get(`/orders/${id}/`);
        setOrder(o);
        // Only fetch bank details while there's still something to pay —
        // initiating reuses the open transaction, so the reference is stable.
        if (o.payment?.status === 'unpaid' || o.payment?.status === 'awaiting_payment') {
          const res = await apiClient.post('/payments/initiate/', { order_id: o.id, provider: 'direct_deposit' });
          setPayment(res.payment);
          setTransactionId(res.transaction.id);
          setBankReference(res.payment.reference);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, id]);

  async function handleSubmitProof(e) {
    e.preventDefault();
    if (!file) { setSubmitError('Choose your proof of payment file.'); return; }
    setSubmitError('');
    setSubmitting(true);
    try {
      const { url } = await uploadFile('/payments/deposit-proofs/upload/', file);
      await apiClient.post('/payments/deposit-proofs/', {
        transaction: transactionId,
        file_url: url,
        bank_reference_number: bankReference.trim() || payment.reference,
      });
      setOrder(o => ({ ...o, payment: { ...o.payment, status: 'proof_submitted' } }));
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) return <Spinner />;
  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to pay for your order.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }
  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  const status = order.payment?.status;

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Pay for order <span className="font-mono">#{order.id}</span></h1>
      <p className="text-sm text-gray-500 mb-6">
        Total due: <span className="font-semibold text-brand-green font-mono">R{Number(order.total).toFixed(2)}</span>
      </p>

      {status === 'paid' && (
        <Notice tone="green">We&apos;ve received your payment, thank you. The farm is preparing your order.</Notice>
      )}
      {status === 'credit' && (
        <Notice tone="gray">This order is on your business account and will be invoiced on delivery.</Notice>
      )}
      {status === 'proof_submitted' && (
        <Notice tone="blue">
          We&apos;ve received your proof of payment. Your order goes to the farmers as soon as the money has cleared in our bank account. EFTs from other banks can take a day or two. You&apos;ll get a notification once it&apos;s confirmed.
        </Notice>
      )}

      {payment && status !== 'proof_submitted' && (
        <>
          <div className="bg-white rounded border border-hairline p-4 mb-4">
            <h2 className="font-semibold text-gray-700 mb-3">1. Pay by EFT or bank deposit</h2>
            <BankDetails details={payment} amount={payment.amount} reference={payment.reference} />
            <p className="text-xs text-gray-500 mt-3">
              Use the reference exactly as shown so we can match your payment to this order.
            </p>
          </div>

          <form onSubmit={handleSubmitProof} className="bg-white rounded border border-hairline p-4">
            <h2 className="font-semibold text-gray-700 mb-3">2. Upload your proof of payment</h2>
            <label className="block text-sm font-medium text-gray-700 mb-1">Proof of payment (PDF or image, max 5 MB)</label>
            <input
              type="file"
              accept="application/pdf,image/jpeg,image/png,image/webp"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-gray-600 mb-4 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-brand-green/10 file:text-brand-green file:font-medium"
            />
            <label className="block text-sm font-medium text-gray-700 mb-1">Reference you used</label>
            <input
              type="text"
              value={bankReference}
              onChange={e => setBankReference(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono mb-4 focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
            />
            {submitError && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{submitError}</div>
            )}
            <button type="submit" disabled={submitting} className="w-full btn-primary py-3 disabled:opacity-60">
              {submitting ? 'Uploading…' : 'Submit proof of payment'}
            </button>
          </form>
        </>
      )}

      <p className="text-center mt-6">
        <Link href="/orders" className="text-sm text-brand-green font-medium hover:underline">Back to your orders</Link>
      </p>
    </div>
  );
}

const NOTICE_TONES = {
  green: 'bg-green-50 border-green-200 text-green-800',
  blue: 'bg-blue-50 border-blue-200 text-blue-800',
  gray: 'bg-gray-50 border-gray-200 text-gray-700',
};

function Notice({ tone, children }) {
  return <div className={`mb-4 border rounded-lg px-4 py-3 text-sm ${NOTICE_TONES[tone]}`}>{children}</div>;
}
