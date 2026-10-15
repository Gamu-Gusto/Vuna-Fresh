'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

/**
 * Approved drivers for the assign controls, with buyers' ratings. Fetch once
 * per page and pass the list to every AssignDriver on it.
 */
export function useApprovedDrivers() {
  const [drivers, setDrivers] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    apiClient.get('/admin/drivers/')
      .then(list => setDrivers(list.filter(d => d.is_approved)))
      .catch(() => setError('Could not load drivers.'));
  }, []);
  return { drivers, error };
}

// e.g. "Sipho Nkosi (Bakkie, 4.5★)"
function driverLabel(d) {
  const details = [d.vehicle_type, d.rating_count ? `${d.average_rating.toFixed(1)}★` : null].filter(Boolean);
  return `${d.full_name || d.email}${details.length ? ` (${details.join(', ')})` : ''}`;
}

/**
 * Driver picker + Assign button for one order that is being packed or is ready
 * for pickup (the only statuses the backend accepts). onAssigned receives the
 * updated order.
 */
export default function AssignDriver({ order, drivers, onAssigned, compact = false }) {
  const [driverId, setDriverId] = useState(order.driver ? String(order.driver) : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  if (drivers && drivers.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No approved drivers yet. Approve one on the{' '}
        <Link href="/admin/approvals" className="text-brand-green hover:underline">Approvals</Link> page.
      </p>
    );
  }

  async function assign() {
    setError('');
    setSaving(true);
    try {
      onAssigned(await apiClient.post(`/orders/${order.id}/assign_driver/`, { driver_id: Number(driverId) }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const unchanged = String(order.driver ?? '') === driverId;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <label className="sr-only" htmlFor={`driver-${order.id}`}>Driver for order #{order.id}</label>
        <select
          id={`driver-${order.id}`}
          value={driverId}
          onChange={e => setDriverId(e.target.value)}
          disabled={!drivers}
          className={`border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white ${compact ? 'min-w-0 flex-1' : 'min-w-56'}`}
        >
          <option value="">{drivers ? 'Choose a driver…' : 'Loading drivers…'}</option>
          {(drivers ?? []).map(d => <option key={d.id} value={d.id}>{driverLabel(d)}</option>)}
        </select>
        <button
          onClick={assign}
          disabled={!driverId || saving || unchanged}
          className="btn-primary text-sm px-4 py-1.5 disabled:opacity-60"
        >
          {saving ? 'Assigning…' : order.driver ? 'Change' : 'Assign'}
        </button>
      </div>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}
