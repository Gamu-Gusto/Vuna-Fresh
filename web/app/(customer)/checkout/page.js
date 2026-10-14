'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useCart } from '@/lib/cart-context';
import { apiClient } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Spinner from '@/components/Spinner';

export default function CheckoutPage() {
  const { user } = useAuth();
  const { cart, loading: cartLoading, fetchCart } = useCart();
  const router = useRouter();

  const [addresses, setAddresses] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState('');
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    apiClient.get('/users/me/addresses/').then(data => {
      const list = data.results ?? data;
      setAddresses(list);
      const def = list.find(a => a.is_default);
      if (def) setSelectedAddress(String(def.id));
    }).catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to checkout.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }

  if (cartLoading) return <Spinner />;

  const items = cart?.items ?? [];
  const total = cart?.cart_total ?? 0;

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400 mb-4">Your cart is empty.</p>
        <Link href="/products" className="text-brand-green font-medium hover:underline">Browse products</Link>
      </div>
    );
  }

  async function handlePlaceOrder() {
    if (!selectedAddress) { setError('Please select a delivery address.'); return; }
    setError('');
    setPlacing(true);
    try {
      const order = await apiClient.post('/orders/', {
        delivery_address_id: Number(selectedAddress),
      });
      // The cart just placed is now 'converted' server-side — refresh so the
      // cart context picks up the new (empty) active cart instead of holding
      // onto stale items that the backend will correctly 404 on if touched.
      await fetchCart();
      // Business orders on credit terms are invoiced on delivery; everyone
      // else pays by EFT next, using the bank details on the pay page.
      router.push(order.payment?.status === 'credit' ? `/orders?placed=${order.id}` : `/orders/${order.id}/pay`);
    } catch (err) {
      setError(err.message);
    } finally {
      setPlacing(false);
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Checkout</h1>

      {/* Order summary */}
      <div className="bg-white rounded border border-hairline p-4 mb-4">
        <h2 className="font-semibold text-gray-700 mb-3">Order summary</h2>
        {items.map(item => (
          <div key={item.id} className="flex justify-between text-sm py-1">
            <span className="text-gray-600">{item.product_name} × <span className="font-mono">{item.quantity}</span></span>
            <span className="font-medium font-mono">R{Number(item.line_total).toFixed(2)}</span>
          </div>
        ))}
        <div className="border-t border-hairline mt-3 pt-3 flex justify-between font-semibold">
          <span>Total</span>
          <span className="text-brand-green font-mono">R{Number(total).toFixed(2)}</span>
        </div>
      </div>

      {/* Delivery address */}
      <div className="bg-white rounded border border-hairline p-4 mb-4">
        <h2 className="font-semibold text-gray-700 mb-3">Delivery address</h2>
        {addresses.length === 0 ? (
          <p className="text-sm text-gray-400">
            No addresses saved.{' '}
            <Link href="/profile/addresses" className="text-brand-green underline">Add one</Link>
          </p>
        ) : (
          <div className="space-y-2">
            {addresses.map(addr => (
              <label key={addr.id} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="address"
                  value={addr.id}
                  checked={selectedAddress === String(addr.id)}
                  onChange={() => setSelectedAddress(String(addr.id))}
                  className="mt-0.5"
                />
                <span className="text-sm text-gray-700">
                  {addr.street_address}, {addr.suburb && `${addr.suburb}, `}{addr.city}, {addr.province} {addr.postal_code}
                  {addr.is_default && <span className="ml-2 text-xs text-brand-green font-medium">(default)</span>}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Payment method — offline only until a card gateway is live */}
      <div className="bg-white rounded border border-hairline p-4 mb-4">
        <h2 className="font-semibold text-gray-700 mb-2">Payment</h2>
        <label className="flex items-start gap-3">
          <input type="radio" checked readOnly className="mt-0.5" />
          <span className="text-sm text-gray-700">
            <span className="font-medium">EFT / direct bank deposit</span>
            <span className="block text-gray-500 mt-0.5">
              After you place your order you&apos;ll get our bank details and a payment reference.
              Upload your proof of payment and we&apos;ll confirm it.
            </span>
          </span>
        </label>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <button
        onClick={handlePlaceOrder}
        disabled={placing || addresses.length === 0}
        className="w-full btn-primary py-3"
      >
        {placing ? 'Placing order…' : 'Place order'}
      </button>
    </div>
  );
}
