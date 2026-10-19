'use client';

import { useState } from 'react';
import Link from 'next/link';
import { apiClient, apiErrorText } from '@/lib/api';

const FREQUENCIES = [
  { value: 'weekly', label: 'Every week' },
  { value: 'biweekly', label: 'Every 2 weeks' },
  { value: 'monthly', label: 'Every month' },
];

function tomorrow() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

// "Deliver this regularly" form on the product page, for logged-in buyers.
export default function SubscribeForm({ product, quantity }) {
  const [open, setOpen] = useState(false);
  const [frequency, setFrequency] = useState('weekly');
  const [startDate, setStartDate] = useState(tomorrow());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await apiClient.post('/subscriptions/', {
        product: product.id,
        quantity,
        frequency,
        next_delivery_date: startDate,
      });
      setDone(true);
    } catch (err) {
      setError(apiErrorText(err));
    } finally {
      setSaving(false);
    }
  }

  if (done) {
    return (
      <p className="mt-4 text-sm text-green-800 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
        Subscribed! Manage it from <Link href="/subscriptions" className="font-medium underline">your subscriptions</Link>.
      </p>
    );
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="mt-4 block text-sm text-brand-green font-semibold underline underline-offset-4">
        Get this delivered regularly
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 border border-hairline rounded-lg p-4 space-y-3 text-sm">
      <p className="font-medium text-gray-800">
        Subscribe to <span className="font-mono">{quantity}</span> × {product.unit}
      </p>
      <div className="grid grid-cols-2 gap-3">
        <label>
          <span className="block text-gray-600 mb-1">How often</span>
          <select value={frequency} onChange={e => setFrequency(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white">
            {FREQUENCIES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </label>
        <label>
          <span className="block text-gray-600 mb-1">First delivery</span>
          <input type="date" min={tomorrow()} value={startDate} onChange={e => setStartDate(e.target.value)} required className="w-full border border-gray-300 rounded-lg px-3 py-2" />
        </label>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="btn-primary px-4 py-2 disabled:opacity-60">{saving ? 'Subscribing…' : 'Subscribe'}</button>
        <button type="button" onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-700 px-3">Cancel</button>
      </div>
    </form>
  );
}
