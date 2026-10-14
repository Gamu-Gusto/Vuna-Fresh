'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';
import { Stars } from '@/components/ProductReviews';

export default function FarmerReviewsPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/reviews/my_products/')
      .then(data => setReviews(data.results ?? data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  const average = reviews.length ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length : 0;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Reviews</h1>
        {reviews.length > 0 && (
          <p className="text-sm text-gray-500 mt-1">
            <Stars rating={average} /> {average.toFixed(1)} average from {reviews.length} review{reviews.length === 1 ? '' : 's'}
          </p>
        )}
      </div>

      {reviews.length === 0 ? (
        <EmptyState className="py-12">No reviews yet. Buyers can review your products after delivery.</EmptyState>
      ) : (
        <ul className="space-y-3">
          {reviews.map(r => (
            <li key={r.id} className="bg-white rounded border border-hairline p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold text-gray-800">{r.product_name}</span>
                <Stars rating={r.rating} />
              </div>
              {r.comment && <p className="text-gray-700 mt-2 whitespace-pre-line">{r.comment}</p>}
              <p className="text-xs text-gray-400 mt-2">
                {r.buyer_name}, {new Date(r.created_at).toLocaleDateString('en-ZA')}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
