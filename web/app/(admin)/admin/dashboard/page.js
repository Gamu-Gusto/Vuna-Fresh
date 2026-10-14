'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [
          pendingFarmers,
          pendingDrivers,
          customers,
          farmers,
          drivers,
          admins,
          orders,
        ] = await Promise.all([
          apiClient.get('/admin/farmers/?pending=true'),
          apiClient.get('/admin/drivers/?pending=true'),
          apiClient.get('/admin/users/?role=customer&page_size=1'),
          apiClient.get('/admin/users/?role=farmer&page_size=1'),
          apiClient.get('/admin/users/?role=driver&page_size=1'),
          apiClient.get('/admin/users/?role=admin&page_size=1'),
          apiClient.get('/orders/?page_size=1'),
        ]);
        setStats({
          pendingFarmers: pendingFarmers.length,
          pendingDrivers: pendingDrivers.length,
          customers: customers.count,
          farmers: farmers.count,
          drivers: drivers.count,
          admins: admins.count,
          totalOrders: orders.count,
        });
      } catch {
        setError('Could not load dashboard data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  const hasPending = stats.pendingFarmers > 0 || stats.pendingDrivers > 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {hasPending && (
        <div className="bg-amber-50 border border-amber-200 rounded p-4 flex items-center justify-between">
          <div className="text-sm text-amber-800">
            <span className="font-semibold">Approvals needed:</span>{' '}
            {stats.pendingFarmers > 0 && (
              <span>{stats.pendingFarmers} farmer{stats.pendingFarmers !== 1 ? 's' : ''}</span>
            )}
            {stats.pendingFarmers > 0 && stats.pendingDrivers > 0 && <span> and </span>}
            {stats.pendingDrivers > 0 && (
              <span>{stats.pendingDrivers} driver{stats.pendingDrivers !== 1 ? 's' : ''}</span>
            )}
          </div>
          <Link href="/admin/approvals" className="text-sm font-semibold text-amber-700 hover:underline">
            Review
          </Link>
        </div>
      )}

      <div>
        <h2 className="text-base font-semibold text-navy mb-3">Pending approvals</h2>
        <div className="grid grid-cols-2 gap-4">
          <CountCard
            label="Farmers awaiting approval"
            value={stats.pendingFarmers}
            href="/admin/approvals"
            urgent={stats.pendingFarmers > 0}
          />
          <CountCard
            label="Drivers awaiting approval"
            value={stats.pendingDrivers}
            href="/admin/approvals"
            urgent={stats.pendingDrivers > 0}
          />
        </div>
      </div>

      <div>
        <h2 className="text-base font-semibold text-navy mb-3">Users by role</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <CountCard label="Buyers" value={stats.customers} href="/admin/users?role=customer" />
          <CountCard label="Farmers" value={stats.farmers} href="/admin/users?role=farmer" />
          <CountCard label="Drivers" value={stats.drivers} href="/admin/users?role=driver" />
          <CountCard label="Admins" value={stats.admins} href="/admin/users?role=admin" />
        </div>
      </div>

      <div>
        <h2 className="text-base font-semibold text-navy mb-3">Orders</h2>
        <div className="grid grid-cols-2 gap-4">
          <CountCard label="Total orders" value={stats.totalOrders} href="/admin/orders" />
        </div>
      </div>
    </div>
  );
}

function CountCard({ label, value, href, urgent = false }) {
  return (
    <Link
      href={href}
      className={`rounded border p-5 hover:border-brand-green transition-colors block ${
        urgent ? 'bg-amber-50 border-amber-200' : 'bg-white border-hairline'
      }`}
    >
      <p className={`text-3xl font-bold ${urgent ? 'text-amber-600' : 'text-gray-900'}`}>
        {value}
      </p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </Link>
  );
}
