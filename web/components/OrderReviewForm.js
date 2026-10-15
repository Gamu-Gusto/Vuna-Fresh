'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api';
import { StarPicker } from './SupportCenter';

// Lets a buyer rate the driver and review each product in a delivered order.
// The backend only accepts these for delivered orders: one driver rating per
// order and one review per product per order.
export default function OrderReviewForm({ order }) {
  const products = [...new Map(order.items.map(i => [i.product, i])).values()];
  const [open, setOpen] = useState(false);
  const canRateDriver = order.driver && !order.driver_review;

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm text-brand-green font-medium hover:underline">
        {canRateDriver ? 'Rate your delivery and products' : 'Review these products'}
      </button>
    );
  }

  return (
    <div className="space-y-3">
      {canRateDriver && <DriverRatingRow order={order} />}
      {products.map(item => <ReviewRow key={item.product} orderId={order.id} item={item} />)}
      <button onClick={() => setOpen(false)} className="text-xs text-gray-500 hover:text-gray-700">Close</button>
    </div>
  );
}

function DriverRatingRow({ order }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [state, setState] = useState('idle'); // idle | saving | done
  const [error, setError] = useState('');
  const driver = order.driver_name || 'your driver';

  async function submit() {
    setError('');
    setState('saving');
    try {
      await apiClient.post('/driver-reviews/', { order: order.id, rating, comment: comment.trim() });
      setState('done');
    } catch (err) {
      setError(err.message);
      setState('idle');
    }
  }

  if (state === 'done') {
    return <p className="text-sm text-green-700">Thanks for rating {driver}.</p>;
  }

  return (
    <div className="border border-hairline rounded-lg p-3 text-sm space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-gray-800">Delivery by {driver}</span>
        <StarPicker value={rating} onChange={setRating} />
      </div>
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        rows={2}
        placeholder="How was the delivery and service? (optional)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
      {error && <p className="text-red-600">{error}</p>}
      <button onClick={submit} disabled={!rating || state === 'saving'} className="btn-primary text-sm px-3 py-1.5 disabled:opacity-60">
        {state === 'saving' ? 'Saving…' : 'Rate driver'}
      </button>
    </div>
  );
}

function ReviewRow({ orderId, item }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [state, setState] = useState('idle'); // idle | saving | done
  const [error, setError] = useState('');

  async function submit() {
    setError('');
    setState('saving');
    try {
      await apiClient.post('/reviews/', { product: item.product, order: orderId, rating, comment: comment.trim() });
      setState('done');
    } catch (err) {
      setError(err.message);
      setState('idle');
    }
  }

  if (state === 'done') {
    return <p className="text-sm text-green-700">Thanks for reviewing {item.product_name}.</p>;
  }

  return (
    <div className="border border-hairline rounded-lg p-3 text-sm space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-gray-800">{item.product_name}</span>
        <StarPicker value={rating} onChange={setRating} />
      </div>
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        rows={2}
        placeholder="How was it? (optional)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
      {error && <p className="text-red-600">{error}</p>}
      <button onClick={submit} disabled={!rating || state === 'saving'} className="btn-primary text-sm px-3 py-1.5 disabled:opacity-60">
        {state === 'saving' ? 'Saving…' : 'Post review'}
      </button>
    </div>
  );
}
