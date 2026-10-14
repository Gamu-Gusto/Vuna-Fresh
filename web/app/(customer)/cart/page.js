'use client';

import { useCart } from '@/lib/cart-context';
import { useAuth } from '@/lib/auth-context';
import CartItemRow from '@/components/CartItemRow';
import Spinner from '@/components/Spinner';
import EmptyState from '@/components/EmptyState';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function CartPage() {
  const { cart, loading } = useCart();
  const { user } = useAuth();
  const router = useRouter();

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to view your cart.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }

  if (loading) return <Spinner />;

  const items = cart?.items ?? [];
  const total = cart?.cart_total ?? 0;

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Your cart</h1>

      {items.length === 0 ? (
        <EmptyState className="py-16">
          <span className="block mb-4">Your cart is empty.</span>
          <Link href="/products" className="text-brand-green font-medium hover:underline">Browse products</Link>
        </EmptyState>
      ) : (
        <>
          <div className="bg-white rounded border border-hairline p-4">
            {items.map(item => <CartItemRow key={item.id} item={item} />)}
          </div>

          <div className="mt-4 bg-white rounded border border-hairline p-4 flex justify-between items-center">
            <span className="font-semibold text-gray-700">Total</span>
            <span className="text-xl font-bold text-brand-green font-mono">R{Number(total).toFixed(2)}</span>
          </div>

          <button
            onClick={() => router.push('/checkout')}
            className="mt-4 w-full btn-primary py-3"
          >
            Proceed to checkout
          </button>
        </>
      )}
    </div>
  );
}
