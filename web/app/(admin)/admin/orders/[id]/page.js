'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import PaymentStatusBadge from '@/components/PaymentStatusBadge';

export default function AdminOrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get(`/orders/${id}/`)
      .then(setOrder)
      .catch(() => setError('Could not load order.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (!order) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  const byFarm = {};
  for (const item of order.items) {
    if (!byFarm[item.farm_name]) byFarm[item.farm_name] = [];
    byFarm[item.farm_name].push(item);
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-2 text-sm">
        <Link href="/admin/orders" className="text-gray-400 hover:text-gray-600">← Orders</Link>
        <span className="text-gray-300">/</span>
        <span className="font-semibold text-gray-900 font-mono">Order #{order.id}</span>
        <OrderStatusBadge status={order.status} />
      </div>

      {/* Overview */}
      <div className="bg-white rounded border border-hairline p-5 grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
        <Detail label="Buyer" value={order.buyer_email} />
        <Detail label="Order date" value={new Date(order.created_at).toLocaleString('en-ZA')} />
        <Detail label="Status" value={<OrderStatusBadge status={order.status} />} />
        <Detail label="Payment" value={<PaymentStatusBadge status={order.payment?.status} />} />
        <Detail
          label="Scheduled delivery"
          value={order.scheduled_delivery_time
            ? new Date(order.scheduled_delivery_time).toLocaleString('en-ZA')
            : '—'}
        />
        <Detail label="Driver assigned" value={order.driver ? `${order.driver_name || 'Driver'} (#${order.driver})` : 'Not assigned'} />
        {order.driver_review && (
          <Detail label="Buyer's driver rating" value={`${order.driver_review.rating} / 5`} />
        )}
      </div>

      {order.status === 'ready_for_pickup' && <AssignDriver order={order} onAssigned={setOrder} />}

      {/* Items grouped by farm */}
      <div className="bg-white rounded border border-hairline p-5">
        <h2 className="font-semibold text-gray-900 mb-4">Items</h2>
        {Object.entries(byFarm).map(([farmName, items]) => (
          <div key={farmName} className="mb-4 last:mb-0">
            <p className="text-sm font-semibold text-gray-600 mb-2">{farmName}</p>
            <div className="divide-y divide-gray-50">
              {items.map(item => (
                <div key={item.id} className="py-2 flex justify-between items-center text-sm">
                  <div>
                    <p className="text-gray-900">{item.product_name}</p>
                    <p className="text-xs text-gray-400 font-mono">
                      {item.quantity} × {item.product_unit} @ R{Number(item.price_at_purchase).toFixed(2)}
                    </p>
                  </div>
                  <p className="text-gray-700 font-medium font-mono">R{Number(item.line_total).toFixed(2)}</p>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div className="border-t border-hairline mt-4 pt-4 space-y-1 text-sm">
          <div className="flex justify-between text-gray-500">
            <span>Subtotal</span>
            <span className="font-mono">R{Number(order.subtotal).toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-gray-500">
            <span>Delivery fee</span>
            <span className="font-mono">R{Number(order.delivery_fee).toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-semibold text-gray-900 text-base pt-1">
            <span>Total</span>
            <span className="font-mono">R{Number(order.total).toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Status history */}
      {order.status_history.length > 0 && (
        <div className="bg-white rounded border border-hairline p-5">
          <h2 className="font-semibold text-gray-900 mb-3">Status history</h2>
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

function Detail({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-gray-900">{value}</p>
    </div>
  );
}

// Ready-for-pickup orders need a driver before they can go out for delivery.
function AssignDriver({ order, onAssigned }) {
  const [drivers, setDrivers] = useState(null);
  const [driverId, setDriverId] = useState(order.driver ? String(order.driver) : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/admin/drivers/')
      .then(list => setDrivers(list.filter(d => d.is_approved)))
      .catch(() => setError('Could not load drivers.'));
  }, []);

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

  return (
    <div className="bg-white rounded border border-hairline p-5 text-sm space-y-3">
      <h2 className="font-semibold text-gray-900">{order.driver ? 'Change driver' : 'Assign a driver'}</h2>
      {drivers && drivers.length === 0 ? (
        <p className="text-gray-500">No approved drivers yet. Approve one on the <Link href="/admin/approvals" className="text-brand-green hover:underline">Approvals</Link> page.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          <select value={driverId} onChange={e => setDriverId(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 bg-white min-w-56">
            <option value="">Choose a driver…</option>
            {(drivers ?? []).map(d => (
              <option key={d.id} value={d.id}>
                {d.full_name || d.email}
                {d.vehicle_type ? ` (${d.vehicle_type})` : ''}
                {d.rating_count ? ` · ${d.average_rating.toFixed(1)}★ from ${d.rating_count}` : ' · no ratings yet'}
              </option>
            ))}
          </select>
          <button onClick={assign} disabled={!driverId || saving || String(order.driver) === driverId} className="btn-primary px-4 py-1.5 disabled:opacity-60">
            {saving ? 'Assigning…' : 'Assign'}
          </button>
        </div>
      )}
      {error && <p className="text-red-600">{error}</p>}
    </div>
  );
}
