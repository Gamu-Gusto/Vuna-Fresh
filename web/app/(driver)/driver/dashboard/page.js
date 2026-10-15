'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import {
  DashboardGrid, DashboardError, DashboardLoading, GreetingCard, HeroBanner, Panel,
  RailItem, StatRow, StatTile, WeeklyBars, weeklyTotals,
} from '@/components/dashboard/widgets';

const deliveredAt = order =>
  order.status_history?.findLast?.(h => h.status === 'delivered')?.changed_at ?? order.created_at;

export default function DriverDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        // Requires an approved driver: 403 means the application is still being checked
        const profile = await apiClient.get('/users/me/profile/driver/');
        const [orders, summary, recent] = await Promise.all([
          apiClient.get('/orders/'),
          // Ratings are a nice-to-have: if they fail, still show the deliveries
          apiClient.get('/driver-reviews/summary/').catch(() => null),
          apiClient.get('/driver-reviews/').catch(() => null),
        ]);
        setData({
          profile,
          orders: orders.results ?? [],
          ratings: summary && recent ? { summary, recent: (recent.results ?? []).slice(0, 4) } : null,
        });
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) setPending(true);
        else setError(err.message);
      }
    }
    load();
  }, []);

  if (pending) {
    return (
      <div className="max-w-xl mt-8">
        <HeroBanner
          kicker="Driver application"
          title="We're checking your application"
          body="Someone from the Vuna Fresh team will look at your driver account. Your deliveries will show up here once it's approved."
        />
        <p className="mt-6 text-sm text-gray-500">Signed in as {user?.email}</p>
      </div>
    );
  }
  if (error) return <DashboardError message={error} />;
  if (!data) return <DashboardLoading />;

  const { profile, orders, ratings } = data;
  const toCollect = orders.filter(o => o.status === 'ready_for_pickup');
  const onTheRoad = orders.filter(o => o.status === 'out_for_delivery');
  const delivered = orders.filter(o => o.status === 'delivered');
  const vehicle = [profile.vehicle_type, profile.vehicle_registration].filter(Boolean).join(', ');

  return (
    <DashboardGrid
      main={
        <>
          <DriverHero toCollect={toCollect} onTheRoad={onTheRoad} />

          <StatRow>
            <StatTile icon="box" label="To collect" value={toCollect.length} tone={toCollect.length ? 'attention' : 'normal'} />
            <StatTile icon="truck" label="On the road" value={onTheRoad.length} />
            <StatTile icon="check" label="Delivered" value={delivered.length} />
          </StatRow>

          <Panel title="Active deliveries">
            <DeliveryTable
              orders={[...onTheRoad, ...toCollect]}
              empty="No active deliveries. New ones appear here as soon as the team assigns them to you."
            />
          </Panel>

          <Panel title="Completed deliveries">
            <DeliveryTable orders={delivered.slice(0, 5)} empty="Deliveries you complete will be listed here." />
          </Panel>
        </>
      }
      rail={
        <>
          <GreetingCard user={user} line={vehicle || 'Driver'} />

          <Panel>
            <WeeklyBars
              title="Deliveries per week"
              emptyText="Your weekly deliveries show here once you complete your first one."
              data={weeklyTotals(delivered, {
                dateOf: deliveredAt,
                valueOf: () => 1,
                format: v => `${v} ${v === 1 ? 'delivery' : 'deliveries'}`,
              })}
            />
          </Panel>

          {ratings && <RatingsPanel summary={ratings.summary} recent={ratings.recent} />}
        </>
      }
    />
  );
}

function DriverHero({ toCollect, onTheRoad }) {
  if (onTheRoad.length > 0) {
    const order = onTheRoad[0];
    return (
      <HeroBanner
        kicker="On the road"
        title={`Order #${order.id} is with you`}
        body="Hand it to the buyer, then confirm the delivery. That's what lets the farmers be paid."
        action={{ href: `/driver/deliveries/${order.id}`, label: 'Open delivery' }}
      />
    );
  }
  if (toCollect.length > 0) {
    const order = toCollect[0];
    return (
      <HeroBanner
        kicker="Ready for pickup"
        title={toCollect.length === 1 ? `Collect order #${order.id}` : `${toCollect.length} orders to collect`}
        body="The farms have packed these orders. Open one to see the pickup stops and where it's going."
        action={{ href: `/driver/deliveries/${order.id}`, label: 'See pickup stops' }}
      />
    );
  }
  return (
    <HeroBanner
      kicker="Deliveries"
      title="No deliveries right now"
      body="When the team assigns you an order, it appears here with every farm to collect from and the buyer's address."
    />
  );
}

function DeliveryTable({ orders, empty }) {
  if (orders.length === 0) {
    return <p className="rounded-2xl bg-brand-bg px-5 py-8 text-center text-sm text-gray-600">{empty}</p>;
  }
  return (
    <ul className="divide-y divide-[#EEF1EC] -my-2">
      {orders.map(order => (
        <li key={order.id}>
          <Link
            href={`/driver/deliveries/${order.id}`}
            className="flex items-center justify-between gap-4 py-3 hover:text-brand-green"
          >
            <span>
              <span className="block font-semibold text-navy tabular-nums">Order #{order.id}</span>
              <span className="block text-xs text-gray-500">
                {order.scheduled_delivery_time
                  ? `Deliver by ${new Date(order.scheduled_delivery_time).toLocaleString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}`
                  : `Ordered ${new Date(order.created_at).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })}`}
              </span>
            </span>
            <OrderStatusBadge status={order.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

// Buyers rate each delivery after it arrives. Drivers see the rating and
// comment, not who wrote it.
function RatingsPanel({ summary, recent }) {
  return (
    <Panel title="Your rating">
      {summary.count === 0 ? (
        <p className="text-sm text-gray-500">No ratings yet. Buyers can rate each delivery once it arrives.</p>
      ) : (
        <>
          <p className="flex items-baseline gap-2">
            <span className="type-display text-[2.5rem] text-navy">{summary.average.toFixed(1)}</span>
            <span className="text-amber-500" aria-hidden="true">★</span>
            <span className="text-sm text-gray-500">from {summary.count} {summary.count === 1 ? 'rating' : 'ratings'}</span>
          </p>
          <ul className="divide-y divide-[#EEF1EC] mt-2">
            {recent.map(r => (
              <RailItem
                key={r.id}
                badge={
                  <span className="w-14 shrink-0 text-amber-500 text-xs" aria-label={`${r.rating} out of 5 stars`}>
                    {'★'.repeat(r.rating)}<span className="text-gray-300">{'★'.repeat(5 - r.rating)}</span>
                  </span>
                }
                title={`Order #${r.order}`}
                subtitle={r.comment || 'No comment'}
              />
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
