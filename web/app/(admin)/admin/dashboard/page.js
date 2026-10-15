'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import PaymentStatusBadge from '@/components/PaymentStatusBadge';
import {
  DashboardGrid, DashboardError, DashboardLoading, GreetingCard, HeroBanner, Panel,
  RailItem, StatRow, StatTile, WeeklyBars, weeklyTotals,
} from '@/components/dashboard/widgets';

const CHART_WEEKS = 6;

// Orders come newest first, so page back only until the chart's window is covered
async function ordersSince(since) {
  const orders = [];
  let page = 1;
  for (;;) {
    const data = await apiClient.get(`/orders/?page=${page}`);
    const results = data.results ?? [];
    orders.push(...results);
    const oldest = results[results.length - 1];
    if (!data.next || !oldest || new Date(oldest.created_at) < since) return { orders, count: data.count };
    page += 1;
  }
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      const since = new Date();
      since.setDate(since.getDate() - 7 * CHART_WEEKS);
      try {
        const [pendingFarmers, pendingDrivers, proofs, payouts, recent, ...roleCounts] = await Promise.all([
          apiClient.get('/admin/farmers/?pending=true'),
          apiClient.get('/admin/drivers/?pending=true'),
          apiClient.get('/payments/deposit-proofs/pending/'),
          apiClient.get('/payments/payouts/?status=pending'),
          ordersSince(since),
          ...['customer', 'farmer', 'driver'].map(role => apiClient.get(`/admin/users/?role=${role}`)),
        ]);
        setData({
          pendingFarmers,
          pendingDrivers,
          proofCount: proofs.count ?? (proofs.results ?? proofs).length,
          payouts: payouts.results ?? [],
          orders: recent.orders,
          orderCount: recent.count,
          people: { buyers: roleCounts[0].count, farmers: roleCounts[1].count, drivers: roleCounts[2].count },
        });
      } catch {
        setError('Could not load the dashboard. Check your connection and try again.');
      }
    }
    load();
  }, []);

  if (error) return <DashboardError message={error} />;
  if (!data) return <DashboardLoading />;

  const { pendingFarmers, pendingDrivers, proofCount, payouts, orders, orderCount, people } = data;
  const approvals = [
    ...pendingFarmers.map(f => ({ key: `f${f.id}`, name: f.farm_name || f.full_name || f.email, kind: 'Farmer' })),
    ...pendingDrivers.map(d => ({ key: `d${d.id}`, name: d.full_name || d.email, kind: 'Driver' })),
  ];
  const readyPayouts = payouts.filter(p => p.ready_to_pay);
  const readyTotal = readyPayouts.reduce((s, p) => s + Number(p.net_amount), 0);

  return (
    <DashboardGrid
      main={
        <>
          <AdminHero proofCount={proofCount} approvalCount={approvals.length} readyPayouts={readyPayouts} readyTotal={readyTotal} />

          <StatRow>
            <StatTile icon="banknote" label="Payments to verify" value={proofCount} href="/admin/payments" tone={proofCount ? 'attention' : 'normal'} />
            <StatTile icon="check" label="Waiting for approval" value={approvals.length} href="/admin/approvals" tone={approvals.length ? 'attention' : 'normal'} />
            <StatTile icon="wallet" label="Payouts ready" value={readyPayouts.length} href="/admin/payouts" />
          </StatRow>

          <Panel title="Recent orders" action={{ href: '/admin/orders', label: 'See all' }}>
            {orders.length === 0 ? (
              <p className="rounded-2xl bg-brand-bg px-5 py-8 text-center text-sm text-gray-600">No orders yet.</p>
            ) : (
              <div className="overflow-x-auto -mx-5 sm:-mx-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-[#EEF1EC]">
                      <th className="font-medium px-5 sm:px-6 py-2">Order</th>
                      <th className="font-medium px-3 py-2 hidden md:table-cell">Buyer</th>
                      <th className="font-medium px-3 py-2 hidden sm:table-cell">Payment</th>
                      <th className="font-medium px-3 py-2">Status</th>
                      <th className="font-medium px-5 sm:px-6 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EEF1EC]">
                    {orders.slice(0, 6).map(order => (
                      <tr key={order.id} className="hover:bg-brand-bg/60">
                        <td className="px-5 sm:px-6 py-3">
                          <Link href={`/admin/orders/${order.id}`} className="font-semibold text-navy hover:text-brand-green tabular-nums">#{order.id}</Link>
                        </td>
                        <td className="px-3 py-3 text-gray-600 max-w-[12rem] truncate hidden md:table-cell">{order.buyer_email}</td>
                        <td className="px-3 py-3 hidden sm:table-cell"><PaymentStatusBadge status={order.payment?.status} /></td>
                        <td className="px-3 py-3"><OrderStatusBadge status={order.status} /></td>
                        <td className="px-5 sm:px-6 py-3 text-right font-semibold text-navy tabular-nums">R{Number(order.total).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel title="People on Vuna Fresh" action={{ href: '/admin/users', label: 'Manage users' }}>
            <dl className="grid grid-cols-3 gap-3">
              {[['Buyers', people.buyers, 'customer'], ['Farmers', people.farmers, 'farmer'], ['Drivers', people.drivers, 'driver']].map(([label, value, role]) => (
                <Link key={role} href={`/admin/users?role=${role}`} className="rounded-2xl bg-brand-bg px-4 py-3 hover:bg-leaf transition-colors">
                  <dt className="text-sm text-gray-500">{label}</dt>
                  <dd className="type-display text-[2rem] text-navy">{value}</dd>
                </Link>
              ))}
            </dl>
          </Panel>
        </>
      }
      rail={
        <>
          <GreetingCard user={user} line={`${orderCount} ${orderCount === 1 ? 'order' : 'orders'} placed so far`} />

          <Panel>
            <WeeklyBars
              title="Orders per week"
              emptyText="Weekly orders show here once buyers start ordering."
              data={weeklyTotals(orders, {
                weeks: CHART_WEEKS,
                dateOf: o => o.created_at,
                valueOf: () => 1,
                format: v => `${v} ${v === 1 ? 'order' : 'orders'}`,
              })}
            />
          </Panel>

          <Panel title="Waiting for approval" action={approvals.length ? { href: '/admin/approvals', label: 'Review' } : undefined}>
            {approvals.length === 0 ? (
              <p className="text-sm text-gray-500">No farmers or drivers are waiting.</p>
            ) : (
              <ul className="divide-y divide-[#EEF1EC] -my-3">
                {approvals.slice(0, 5).map(a => (
                  <RailItem
                    key={a.key}
                    badge={
                      <span className="w-10 h-10 shrink-0 rounded-full bg-leaf text-brand-green grid place-items-center text-sm font-semibold" aria-hidden="true">
                        {a.name.slice(0, 1).toUpperCase()}
                      </span>
                    }
                    title={a.name}
                    subtitle={a.kind}
                    action={
                      <Link href="/admin/approvals" className="text-xs font-semibold text-brand-green border border-brand-green/30 rounded-full px-3 py-1.5 hover:bg-leaf">
                        Review
                      </Link>
                    }
                  />
                ))}
              </ul>
            )}
          </Panel>
        </>
      }
    />
  );
}

function AdminHero({ proofCount, approvalCount, readyPayouts, readyTotal }) {
  if (proofCount > 0) {
    return (
      <HeroBanner
        kicker="Payments"
        title={`${proofCount} ${proofCount === 1 ? 'payment' : 'payments'} to verify`}
        body="Check each deposit has cleared in the bank account. Orders only go to the farmers once you confirm the funds."
        action={{ href: '/admin/payments', label: 'Verify payments' }}
      />
    );
  }
  if (approvalCount > 0) {
    return (
      <HeroBanner
        kicker="Approvals"
        title={`${approvalCount} ${approvalCount === 1 ? 'application' : 'applications'} waiting`}
        body="New farmers and drivers can't sell or deliver until you approve them."
        action={{ href: '/admin/approvals', label: 'Review applications' }}
      />
    );
  }
  if (readyPayouts.length > 0) {
    return (
      <HeroBanner
        kicker="Farmer payouts"
        title={`R${Math.round(readyTotal).toLocaleString('en-ZA')} ready to pay`}
        body={`${readyPayouts.length} delivered ${readyPayouts.length === 1 ? 'order is' : 'orders are'} waiting for the farm payment.`}
        action={{ href: '/admin/payouts', label: 'Pay farmers' }}
      />
    );
  }
  return (
    <HeroBanner
      kicker="Today"
      title="Nothing needs you right now"
      body="No payments to verify, no applications waiting and no payouts due. New work shows up here first."
      action={{ href: '/admin/orders', label: 'See orders' }}
    />
  );
}
