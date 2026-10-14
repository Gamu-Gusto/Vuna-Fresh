'use client';

import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import PaymentStatusBadge from '@/components/PaymentStatusBadge';

const FARMER_NEXT_STATUS = {
  placed: 'preparing',
  preparing: 'ready_for_pickup',
};

const NEXT_STATUS_LABEL = {
  preparing: 'Mark as Preparing',
  ready_for_pickup: 'Mark as Ready for Pickup',
};

export default function FarmerOrderDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [order, setOrder] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [o, p] = await Promise.all([
          apiClient.get(`/orders/${id}/`),
          apiClient.get('/users/me/profile/farmer/'),
        ]);
        setOrder(o);
        setProfile(p);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          router.replace('/farmer/dashboard');
        } else {
          setError('Could not load order.');
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, router]);

  async function updateStatus(newStatus) {
    setUpdating(true);
    setError('');
    try {
      const updated = await apiClient.post(`/orders/${id}/update_status/`, { status: newStatus });
      setOrder(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (!order) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  const myItems = profile
    ? order.items.filter(item => item.farmer === profile.id)
    : order.items;

  const myTotal = myItems.reduce((sum, item) => sum + Number(item.line_total), 0);
  const nextStatus = FARMER_NEXT_STATUS[order.status];

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-2 text-sm">
        <Link href="/farmer/orders" className="text-gray-400 hover:text-gray-600">← Orders</Link>
        <span className="text-gray-300">/</span>
        <span className="font-semibold text-gray-800 font-mono">Order #{order.id}</span>
        <OrderStatusBadge status={order.status} />
        <PaymentStatusBadge status={order.payment?.status} />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <div className="bg-white rounded border border-hairline p-5 space-y-2 text-sm">
        <h2 className="font-semibold text-gray-800 mb-3">Order details</h2>
        <p className="text-gray-500">
          Buyer: <span className="text-gray-800">{order.buyer_email}</span>
        </p>
        <p className="text-gray-500">
          Placed: <span className="text-gray-800">{new Date(order.created_at).toLocaleString('en-ZA')}</span>
        </p>
        <p className="text-gray-500">
          Order total: <span className="text-gray-800 font-medium font-mono">R{Number(order.total).toFixed(2)}</span>
        </p>
      </div>

      <div className="bg-white rounded border border-hairline p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Your items</h2>
        {myItems.length === 0 ? (
          <p className="text-sm text-gray-400">No items from your farm in this order.</p>
        ) : (
          <>
            <div className="divide-y divide-gray-50">
              {myItems.map(item => (
                <div key={item.id} className="py-2.5 flex justify-between items-center text-sm">
                  <div>
                    <p className="font-medium text-gray-800">{item.product_name}</p>
                    <p className="text-xs text-gray-400 font-mono">
                      {item.quantity} × {item.product_unit} @ R{Number(item.price_at_purchase).toFixed(2)}
                    </p>
                  </div>
                  <p className="text-gray-700 font-medium font-mono">R{Number(item.line_total).toFixed(2)}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-hairline flex justify-between text-sm font-semibold text-gray-700">
              <span>Your subtotal</span>
              <span className="font-mono">R{myTotal.toFixed(2)}</span>
            </div>
          </>
        )}
      </div>

      {nextStatus && (
        <div className="bg-white rounded border border-hairline p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Update status</h2>
          <button
            onClick={() => updateStatus(nextStatus)}
            disabled={updating}
            className="btn-primary px-5 py-2"
          >
            {updating ? 'Updating…' : NEXT_STATUS_LABEL[nextStatus]}
          </button>
        </div>
      )}

      {order.status_history.length > 0 && (
        <div className="bg-white rounded border border-hairline p-5">
          <h2 className="font-semibold text-gray-800 mb-3">History</h2>
          <div className="space-y-2">
            {order.status_history.map(h => (
              <div key={h.id} className="flex items-center gap-3 text-xs text-gray-500">
                <OrderStatusBadge status={h.status} />
                <span>{new Date(h.changed_at).toLocaleString('en-ZA')}</span>
                <span>by {h.changed_by_email}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
