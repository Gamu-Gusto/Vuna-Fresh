'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function FarmerLoginPage() {
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
      if (me.role !== 'farmer') {
        setError('This portal is for farmers only. Please use the correct login for your account type.');
        return;
      }
      const profile = await apiClient.get('/users/me/profile/farmer/');
      router.push(profile.is_approved ? '/farmer/dashboard' : '/farmer/pending');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-12 px-4 pb-16">
      <div className="mb-6">
        <h1 className="type-display text-5xl">Farmer log in</h1>
        <p className="text-gray-600 mt-2">Manage your produce, orders and payouts.</p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
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
        New farmer?{' '}
        <Link href="/signup?role=farmer" className="text-brand-green font-medium hover:underline">
          Apply to sell on Vuna Fresh
        </Link>
      </p>
    </div>
  );
}
