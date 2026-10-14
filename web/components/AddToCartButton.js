'use client';

import { useState } from 'react';
import { useCart } from '@/lib/cart-context';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';

const ROLE_NAMES = { farmer: 'a farmer', driver: 'a driver', admin: 'an admin' };

export default function AddToCartButton({ productId, quantity = 1, className = '' }) {
  const { addItem } = useCart();
  const { user } = useAuth();
  const router = useRouter();
  const [state, setState] = useState('idle'); // idle | loading | done | error
  const [error, setError] = useState('');

  // Only buyer accounts can order. Farmers, drivers and admins browsing the
  // shop (logins are shared across browser tabs) get told why, instead of a
  // button the backend will refuse.
  if (user && user.role !== 'customer') {
    return (
      <span className="w-full text-sm text-gray-600">
        You&apos;re logged in as {ROLE_NAMES[user.role] ?? user.role}. Use a buyer account to order.
      </span>
    );
  }

  async function handleClick() {
    if (!user) {
      router.push('/login');
      return;
    }
    setError('');
    setState('loading');
    try {
      await addItem(productId, quantity);
      setState('done');
      setTimeout(() => setState('idle'), 1500);
    } catch (e) {
      setError(e.message);
      setState('idle');
    }
  }

  const labels = { idle: 'Add to cart', loading: 'Adding…', done: 'Added' };
  const colours = {
    idle: 'bg-brand-green hover:bg-brand-light',
    loading: 'bg-gray-400 cursor-not-allowed',
    done: 'bg-navy',
  };

  return (
    <span className="inline-flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={state === 'loading'}
        aria-live="polite"
        className={`text-white text-sm font-semibold py-2 px-4 rounded-md transition-colors duration-150 ${colours[state]} ${className}`}
      >
        {labels[state]}
      </button>
      {error && <span role="alert" className="text-xs text-ember text-right max-w-[14rem]">{error}</span>}
    </span>
  );
}
