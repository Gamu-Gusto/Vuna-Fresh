'use client';

import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import EmptyState from '@/components/EmptyState';

// Statuses a driver still needs to act on
const ACTIVE_STATUSES = new Set(['ready_for_pickup', 'out_for_delivery']);

export default function DriverDashboard() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [ratings, setRatings] = useState(null); // { summary, recent }
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Profile endpoint requires IsDriver (approved). 403 = not yet approved.
        await apiClient.get('/users/me/profile/driver/');
        const [data, summary, recent] = await Promise.all([
          apiClient.get('/orders/'),
          // Ratings are a nice-to-have: if they fail, still show the deliveries
          apiClient.get('/driver-reviews/summary/').catch(() => null),
          apiClient.get('/driver-reviews/').catch(() => null),
        ]);
        setOrders(data.results ?? []);
        if (summary && recent) setRatings({ summary, recent: (recent.results ?? []).slice(0, 5) });
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setPending(true);
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  }

  if (pending) {
    return (
      <div className="max-w-xl mt-8">
        <h1 className="type-display text-5xl">We&apos;re checking your application</h1>
        <p className="mt-4 text-gray-700 leading-relaxed">
          Someone from the Vuna Fresh team will look at your driver account. Your deliveries will show up here once
          it&apos;s approved.
        </p>
        <p className="mt-8 text-sm text-gray-500">Logged in as {user?.email}</p>
      </div>
    );
  }

  const active = orders.filter(o => ACTIVE_STATUSES.has(o.status));
  const completed = orders.filter(o => o.status === 'delivered');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">
          Hi, {user?.first_name}
        </h1>
        <p className="text-gray-500 text-sm mt-1">Your assigned deliveries.</p>
      </div>

      <Section title="Active deliveries" count={active.length}>
        {active.length === 0 ? (
          <EmptyState className="p-8">No active deliveries assigned right now.</EmptyState>
        ) : (
          <DeliveryTable orders={active} />
        )}
      </Section>

      <Section title="Completed deliveries" count={completed.length}>
        {completed.length === 0 ? (
          <EmptyState className="p-8">No completed deliveries yet.</EmptyState>
        ) : (
          <DeliveryTable orders={completed} />
        )}
      </Section>

      {ratings && <Ratings summary={ratings.summary} recent={ratings.recent} />}
    </div>
  );
}

// Buyers rate each delivery after it arrives. Drivers see the rating and
// comment, not who wrote it.
function Ratings({ summary, recent }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Your rating</h2>
      {summary.count === 0 ? (
        <EmptyState className="p-8">No ratings yet. Buyers can rate each delivery once it arrives.</EmptyState>
      ) : (
        <div className="bg-white rounded border border-hairline p-5 space-y-4">
          <p className="text-sm text-gray-600">
            <span className="text-2xl font-bold text-gray-900">{summary.average.toFixed(1)}</span>
            <span className="text-amber-500 ml-1" aria-hidden="true">★</span>
            <span className="ml-2">from {summary.count} {summary.count === 1 ? 'rating' : 'ratings'}</span>
          </p>
          <ul className="divide-y divide-gray-50">
            {recent.map(r => (
              <li key={r.id} className="py-2 text-sm">
                <span className="text-amber-500" aria-label={`${r.rating} out of 5 stars`}>
                  {'★'.repeat(r.rating)}<span className="text-gray-300">{'★'.repeat(5 - r.rating)}</span>
                </span>
                <span className="ml-2 text-xs text-gray-400 font-mono">Order #{r.order}</span>
                {r.comment && <p className="text-gray-700 mt-0.5">{r.comment}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Section({ title, count, children }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        {title}
        {count > 0 && (
          <span className="ml-2 text-sm font-normal text-gray-400">({count})</span>
        )}
      </h2>
      {children}
    </div>
  );
}

function DeliveryTable({ orders }) {
  return (
    <div className="bg-white rounded border border-hairline divide-y divide-gray-50">
      {orders.map(order => (
        <Link
          key={order.id}
          href={`/driver/deliveries/${order.id}`}
          className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
        >
          <div>
            <p className="text-sm font-medium text-gray-800 font-mono">Order #{order.id}</p>
            <p className="text-xs text-gray-400">
              {new Date(order.created_at).toLocaleDateString('en-ZA')}
              {order.scheduled_delivery_time && (
                <>, deliver by {new Date(order.scheduled_delivery_time).toLocaleString('en-ZA')}</>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OrderStatusBadge status={order.status} />
          </div>
        </Link>
      ))}
    </div>
  );
}
