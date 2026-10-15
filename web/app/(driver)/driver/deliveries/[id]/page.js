'use client';

import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';

// Only these two transitions are valid for a driver, in this order
const DRIVER_TRANSITIONS = {
  ready_for_pickup: {
    next: 'out_for_delivery',
    label: 'Start delivery',
    description: 'Confirm you have collected all items and are heading to the buyer.',
  },
  out_for_delivery: {
    next: 'delivered',
    label: 'Mark as delivered',
    description: 'Confirm the order has been handed to the buyer.',
    // Delivery is final: it lets Vuna Fresh pay the farmers for this order
    confirm: id => `Confirm order #${id} has been handed to the buyer? This can't be undone, and the farmers will be paid for it.`,
  },
};

export default function DeliveryDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [order, setOrder] = useState(null);
  const [pickup, setPickup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [o, p] = await Promise.all([
          apiClient.get(`/orders/${id}/`),
          apiClient.get(`/orders/${id}/pickup_details/`),
        ]);
        setOrder(o);
        setPickup(p);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          router.replace('/driver/dashboard');
        } else {
          setError('Could not load delivery details.');
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, router]);

  async function updateStatus(newStatus, confirmMessage) {
    if (confirmMessage && !window.confirm(confirmMessage)) return;
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

  const transition = DRIVER_TRANSITIONS[order.status] ?? null;

  // Group pickup items by farm so the driver knows which stop to make first
  const farmGroups = {};
  if (pickup?.items) {
    for (const item of pickup.items) {
      const key = item.farm_name;
      if (!farmGroups[key]) {
        farmGroups[key] = {
          farm_name: item.farm_name,
          farm_location: item.farm_location,
          farmer_email: item.farmer_email,
          farmer_phone: item.farmer_phone,
          items: [],
        };
      }
      farmGroups[key].items.push(item);
    }
  }

  const addr = pickup?.delivery_address;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-2 text-sm">
        <Link href="/driver/dashboard" className="text-gray-400 hover:text-gray-600">
          ← Deliveries
        </Link>
        <span className="text-gray-300">/</span>
        <span className="font-semibold text-gray-800 font-mono">Order #{order.id}</span>
        <OrderStatusBadge status={order.status} />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* Status action — shown only when the driver has an available transition */}
      {transition && (
        <div className="bg-brand-green/5 border border-brand-green/20 rounded p-5">
          <p className="text-sm text-gray-600 mb-3">{transition.description}</p>
          <button
            onClick={() => updateStatus(transition.next, transition.confirm?.(order.id))}
            disabled={updating}
            className="btn-primary px-5 py-2"
          >
            {updating ? 'Updating…' : transition.label}
          </button>
        </div>
      )}

      {/* Pickup stops — one card per farm */}
      {Object.values(farmGroups).length > 0 && (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-800">
            {Object.values(farmGroups).length === 1 ? 'Pickup stop' : 'Pickup stops'}
          </h2>
          {Object.values(farmGroups).map(farm => (
            <div key={farm.farm_name} className="bg-white rounded border border-hairline p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <p className="font-semibold text-gray-800">{farm.farm_name}</p>
                  {farm.farm_location && (
                    <p className="text-sm text-gray-500 mt-0.5">{farm.farm_location}</p>
                  )}
                </div>
                <div className="text-right text-sm shrink-0">
                  {farm.farmer_phone && (
                    <a
                      href={`tel:${farm.farmer_phone}`}
                      className="block text-brand-green font-medium hover:underline"
                    >
                      {farm.farmer_phone}
                    </a>
                  )}
                  {farm.farmer_email && (
                    <a
                      href={`mailto:${farm.farmer_email}`}
                      className="block text-gray-400 text-xs hover:underline mt-0.5"
                    >
                      {farm.farmer_email}
                    </a>
                  )}
                </div>
              </div>
              <div className="divide-y divide-gray-50 border-t border-gray-50 pt-2">
                {farm.items.map(item => (
                  <div key={item.order_item_id} className="py-1.5 flex justify-between text-sm">
                    <span className="text-gray-700">{item.product_name}</span>
                    <span className="text-gray-500 font-mono">
                      {item.quantity} {item.unit}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delivery address */}
      {addr && (
        <div className="bg-white rounded border border-hairline p-5">
          <h2 className="font-semibold text-gray-800 mb-2">Deliver to</h2>
          <address className="not-italic text-sm text-gray-600 leading-relaxed">
            <p>{addr.street_address}</p>
            {addr.suburb && <p>{addr.suburb}</p>}
            <p>{addr.city}, {addr.province} {addr.postal_code}</p>
          </address>
          <p className="mt-2 text-sm text-gray-500">
            Buyer: <span className="text-gray-800">{order.buyer_email}</span>
          </p>
          {order.scheduled_delivery_time && (
            <p className="mt-1 text-sm text-gray-500">
              Deliver by:{' '}
              <span className="text-gray-800">
                {new Date(order.scheduled_delivery_time).toLocaleString('en-ZA')}
              </span>
            </p>
          )}
        </div>
      )}

      {/* Order summary */}
      <div className="bg-white rounded border border-hairline p-5">
        <h2 className="font-semibold text-gray-800 mb-3">Order contents</h2>
        <div className="divide-y divide-gray-50">
          {order.items.map(item => (
            <div key={item.id} className="py-2 flex justify-between items-center text-sm">
              <div>
                <p className="text-gray-800">{item.product_name}</p>
                <p className="text-xs text-gray-400">
                  <span className="font-mono">{item.quantity} × {item.product_unit}</span> from {item.farm_name}
                </p>
              </div>
              <p className="text-gray-700 font-mono">R{Number(item.line_total).toFixed(2)}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-hairline flex justify-between text-sm font-semibold text-gray-700">
          <span>Total</span>
          <span className="font-mono">R{Number(order.total).toFixed(2)}</span>
        </div>
      </div>

      {/* Status history */}
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
