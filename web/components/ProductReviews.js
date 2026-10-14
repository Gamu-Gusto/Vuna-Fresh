'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

export function Stars({ rating, className = '' }) {
  return (
    <span className={`text-amber-500 ${className}`} aria-label={`${rating} out of 5 stars`}>
      {'★'.repeat(Math.round(rating))}
      <span className="text-gray-300">{'★'.repeat(5 - Math.round(rating))}</span>
    </span>
  );
}

// Reviews for one product. Buyers write reviews from their delivered orders.
export default function ProductReviews({ productId }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [count, setCount] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    apiClient.get(`/reviews/?product=${productId}`)
      .then(data => {
        setReviews(data.results ?? data);
        setCount(data.count ?? (data.results ?? data).length);
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, [productId]);

  async function markHelpful(id) {
    try {
      const updated = await apiClient.post(`/reviews/${id}/mark_helpful/`);
      setReviews(rs => rs.map(r => (r.id === id ? { ...r, ...updated } : r)));
    } catch {}
  }

  if (!loaded) return null;

  const average = reviews.length ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length : 0;

  return (
    <section className="mt-14 max-w-2xl">
      <div className="flex items-baseline gap-3 mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Reviews</h2>
        {count > 0 && (
          <span className="text-sm text-gray-500">
            <Stars rating={average} /> {average.toFixed(1)} from {count} review{count === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {reviews.length === 0 ? (
        <p className="text-sm text-gray-600">No reviews yet. Bought this? Review it from your delivered orders.</p>
      ) : (
        <ul className="space-y-3">
          {reviews.map(r => (
            <li key={r.id} className="bg-white rounded border border-hairline p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-gray-800">{r.buyer_name || 'Vuna Fresh buyer'}</span>
                <Stars rating={r.rating} />
              </div>
              {r.comment && <p className="text-gray-700 mt-2 whitespace-pre-line">{r.comment}</p>}
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                <span>{new Date(r.created_at).toLocaleDateString('en-ZA')}</span>
                {user && !r.is_helpful_by_me && (
                  <button onClick={() => markHelpful(r.id)} className="hover:text-brand-green">Helpful?</button>
                )}
                {r.helpful_count > 0 && <span>{r.helpful_count} found this helpful</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
