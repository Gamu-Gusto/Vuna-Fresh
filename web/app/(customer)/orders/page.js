'use client';

import { Suspense, useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import PaymentStatusBadge from '@/components/PaymentStatusBadge';
import OrderReviewForm from '@/components/OrderReviewForm';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

// useSearchParams() needs a Suspense boundary or the production build fails to prerender.
export default function OrdersPage() {
  return (
    <Suspense>
      <OrdersPageContent />
    </Suspense>
  );
}

function OrdersPageContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const placedId = searchParams.get('placed');

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user) return;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get('/orders/');
        setOrders(data.results ?? data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user]);

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to view your orders.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="type-display text-5xl mb-6">Your orders</h1>

      {placedId && (
        <p className="mb-6 border-l-4 border-brand-green pl-4 text-gray-800">
          Order <span className="font-mono">#{placedId}</span> is placed.
        </p>
      )}

      {loading && <Spinner />}
      {error && <ErrorMessage message={error} onRetry={() => window.location.reload()} />}

      {!loading && !error && orders.length === 0 && (
        <EmptyState>
          You haven&apos;t ordered anything yet.{' '}
          <Link href="/products" className="text-brand-green font-semibold underline underline-offset-4">See this week&apos;s produce</Link>
        </EmptyState>
      )}

      <ol className="border-t border-hairline">
        {orders.map(order => {
          const needsPayment = order.status !== 'cancelled' && ['unpaid', 'awaiting_payment'].includes(order.payment?.status);
          return (
            <li key={order.id} className="border-b border-hairline py-6">
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                <h2 className="text-lg font-semibold">
                  Order <span className="font-mono">#{order.id}</span>
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    {new Date(order.created_at).toLocaleDateString('en-ZA', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </span>
                </h2>
                <p className="flex gap-4">
                  <OrderStatusBadge status={order.status} />
                  <PaymentStatusBadge status={order.payment?.status} />
                </p>
              </div>

              <table className="mt-3 w-full text-sm text-gray-700">
                <tbody>
                  {(order.items ?? []).map(item => (
                    <tr key={item.id}>
                      <td className="py-0.5">{item.product_name}, <span className="font-mono">{item.quantity}</span> {item.product_unit}</td>
                      <td className="py-0.5 text-right font-mono">R{Number(item.line_total).toFixed(2)}</td>
                    </tr>
                  ))}
                  <tr className="font-semibold text-navy">
                    <td className="pt-2">Total{order.delivery_address?.city && <span className="font-normal text-gray-500">, delivering to {order.delivery_address.city}</span>}</td>
                    <td className="pt-2 text-right font-mono">R{Number(order.total).toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>

              <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
                {needsPayment && (
                  <Link href={`/orders/${order.id}/pay`} className="btn-primary px-4 py-2 text-sm">
                    Pay R{Number(order.total).toFixed(2)} by EFT
                  </Link>
                )}
                {order.status === 'delivered' && <OrderReviewForm order={order} />}
                <Link href="/support" className="text-sm text-gray-500 hover:text-gray-800 underline underline-offset-4">Report a problem</Link>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
