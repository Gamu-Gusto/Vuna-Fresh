'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import AssignDriver, { useApprovedDrivers } from '@/components/AssignDriver';
import { Panel } from '@/components/dashboard/widgets';

// The delivery board: packed orders waiting for a driver first, then orders a
// driver hasn't collected yet (driver can still be changed), orders on the
// road, and orders the farms are still packing, which can be given a driver
// early so the route can be planned.
const LISTS = {
  needsDriver: '?status=ready_for_pickup&has_driver=false',
  assigned: '?status=ready_for_pickup&has_driver=true',
  onTheRoad: '?status=out_for_delivery',
  packing: '?status=preparing',
};

export default function AdminDeliveriesPage() {
  const { drivers, error: driversError } = useApprovedDrivers();
  const [lists, setLists] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all(Object.entries(LISTS).map(([key, query]) =>
      apiClient.get(`/orders/${query}`).then(data => [key, data.results ?? []])))
      .then(entries => setLists(Object.fromEntries(entries)))
      .catch(() => setError('Could not load deliveries. Check your connection and try again.'));
  }, []);

  // Assigning a packed order moves it from "needs a driver" to "assigned";
  // an order still being packed stays in its list, now showing its driver.
  function onAssigned(updated) {
    setLists(l => (updated.status === 'preparing'
      ? { ...l, packing: l.packing.map(o => (o.id === updated.id ? updated : o)) }
      : {
        ...l,
        needsDriver: l.needsDriver.filter(o => o.id !== updated.id),
        assigned: [updated, ...l.assigned.filter(o => o.id !== updated.id)],
      }));
  }

  if (error) return <p className="py-20 text-center text-sm text-ember">{error}</p>;
  if (!lists) return <p className="py-20 text-center text-sm text-gray-400">Loading deliveries…</p>;

  const driverName = id => {
    const d = drivers?.find(x => x.id === id);
    return d ? d.full_name || d.email : `Driver #${id}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy">Deliveries</h1>
        <p className="text-sm text-gray-500 mt-1">
          Assign a driver once a farm marks an order ready, or earlier while it&apos;s being packed. The driver sees it on their
          dashboard straight away and is told when it&apos;s ready to collect.
        </p>
      </div>
      {driversError && <p className="text-sm text-ember">{driversError}</p>}

      <Panel title={`Needs a driver (${lists.needsDriver.length})`}>
        {lists.needsDriver.length === 0 ? (
          <Empty text="No packed orders are waiting for a driver." />
        ) : (
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {lists.needsDriver.map(order => (
              <li key={order.id} className="py-3 grid gap-3 md:grid-cols-[1fr_minmax(0,24rem)] md:items-center">
                <OrderSummary order={order} />
                <AssignDriver order={order} drivers={drivers} onAssigned={onAssigned} compact />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={`Assigned, not collected yet (${lists.assigned.length})`}>
        {lists.assigned.length === 0 ? (
          <Empty text="No orders are waiting at a farm for their driver." />
        ) : (
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {lists.assigned.map(order => (
              <li key={order.id} className="py-3 grid gap-3 md:grid-cols-[1fr_minmax(0,24rem)] md:items-center">
                <OrderSummary order={order} detail={`Assigned to ${driverName(order.driver)}`} />
                <AssignDriver order={order} drivers={drivers} onAssigned={onAssigned} compact />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={`Being packed (${lists.packing.length})`}>
        {lists.packing.length === 0 ? <Empty text="No farms are packing orders right now." /> : (
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {lists.packing.map(order => (
              <li key={order.id} className="py-3 grid gap-3 md:grid-cols-[1fr_minmax(0,24rem)] md:items-center">
                <OrderSummary
                  order={order}
                  detail={order.driver ? `Assigned early to ${driverName(order.driver)}` : 'You can line up a driver now'}
                />
                <AssignDriver order={order} drivers={drivers} onAssigned={onAssigned} compact />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={`On the road (${lists.onTheRoad.length})`}>
        {lists.onTheRoad.length === 0 ? <Empty text="No orders are out for delivery." /> : (
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {lists.onTheRoad.map(order => (
              <li key={order.id} className="py-3">
                <OrderSummary order={order} detail={`With ${driverName(order.driver)}`} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function OrderSummary({ order, detail }) {
  const farms = [...new Set(order.items.map(i => i.farm_name))];
  return (
    <div className="min-w-0">
      <Link href={`/admin/orders/${order.id}`} className="font-semibold text-navy hover:text-brand-green tabular-nums">
        Order #{order.id}
      </Link>
      <span className="ml-2 text-sm text-gray-500 tabular-nums">R{Number(order.total).toFixed(2)}</span>
      <p className="text-sm text-gray-600 truncate">
        {farms.length === 1 ? `Collect from ${farms[0]}` : `Collect from ${farms.length} farms: ${farms.join(', ')}`}
      </p>
      {detail && <p className="text-xs text-gray-500 mt-0.5">{detail}</p>}
    </div>
  );
}

function Empty({ text }) {
  return <p className="rounded-2xl bg-brand-bg px-5 py-6 text-center text-sm text-gray-600">{text}</p>;
}
