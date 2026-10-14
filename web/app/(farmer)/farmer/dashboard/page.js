'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import EmptyState from '@/components/EmptyState';

export default function FarmerDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [products, setProducts] = useState(null);
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const p = await apiClient.get('/users/me/profile/farmer/');
        if (!p.is_approved) {
          router.replace('/farmer/pending');
          return;
        }
        setProfile(p);
        const [prods, ords] = await Promise.all([
          apiClient.get(`/products/?farmer=${p.id}&page_size=100`),
          apiClient.get('/orders/'),
        ]);
        setProducts(prods);
        setOrders(ords);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  if (loading || (!profile && !error)) {
    return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  }
  if (error) {
    return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;
  }

  const productCount = products?.count ?? 0;
  const allOrders = orders?.results ?? [];
  const actionableCount = allOrders.filter(o => ['placed', 'preparing'].includes(o.status)).length;
  const recentOrders = allOrders.slice(0, 5);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          {profile?.farm_name || `Welcome, ${user?.first_name}`}
        </h1>
        <p className="text-gray-500 text-sm mt-1">{profile?.farm_location || "Here's what's happening today."}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Products listed" value={productCount} href="/farmer/inventory" />
        <StatCard label="Orders needing action" value={actionableCount} href="/farmer/orders" />
        <StatCard label="Total orders" value={allOrders.length} href="/farmer/orders" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">Recent orders</h2>
          <Link href="/farmer/orders" className="text-sm text-brand-green hover:underline">
            View all
          </Link>
        </div>

        {recentOrders.length === 0 ? (
          <EmptyState className="p-10">
            No orders yet. Once buyers order your products they&apos;ll appear here.
          </EmptyState>
        ) : (
          <div className="bg-white rounded border border-hairline divide-y divide-gray-50">
            {recentOrders.map(order => (
              <Link
                key={order.id}
                href={`/farmer/orders/${order.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
              >
                <div>
                  <p className="text-sm font-medium text-gray-800 font-mono">Order #{order.id}</p>
                  <p className="text-xs text-gray-400">{order.buyer_email}</p>
                </div>
                <div className="flex items-center gap-3">
                  <OrderStatusBadge status={order.status} />
                  <span className="text-sm text-gray-700 font-medium font-mono">
                    R{Number(order.total).toFixed(2)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, href }) {
  return (
    <Link
      href={href}
      className="bg-white rounded border border-hairline p-5 hover:border-brand-green transition-colors block"
    >
      <p className="text-3xl font-bold text-brand-green">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </Link>
  );
}
