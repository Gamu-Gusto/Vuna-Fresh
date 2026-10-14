'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient, ApiError } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const me = await login(email, password);
      if (me.role === 'customer') {
        try {
          const buyerProfile = await apiClient.get('/users/me/profile/buyer/');
          if (buyerProfile.buyer_type === 'business') {
            const business = await apiClient.get('/buyers/me/business/');
            router.push(business.approval_status === 'active' ? '/products' : '/business/pending');
            return;
          }
        } catch (err) {
          if (!(err instanceof ApiError)) throw err;
          // No buyer profile / business details — fall through to normal browsing.
        }
      }
      router.push('/products');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="type-display text-5xl mb-6">Log in</h1>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-2.5"
        >
          {loading ? 'Logging in…' : 'Log in'}
        </button>
        <p className="text-right text-sm">
          <Link href="/forgot-password" className="text-brand-green hover:underline">Forgot password?</Link>
        </p>
      </form>

      <p className="mt-4 text-center text-sm text-gray-500">
        No account yet?{' '}
        <Link href="/signup" className="text-brand-green font-medium hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  );
}
