'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';

// Landing page for the emailed reset link: /reset-password?uid=…&token=…
// useSearchParams() needs a Suspense boundary or the production build fails to prerender.
export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}

const LOGIN_PAGES = [
  { href: '/login', label: 'Buyer' },
  { href: '/farmer/login', label: 'Farmer' },
  { href: '/driver/login', label: 'Driver' },
];

function ResetPasswordForm() {
  const params = useSearchParams();
  const uid = params.get('uid');
  const token = params.get('token');

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiClient.post('/auth/password-reset/confirm/', { uid, token, password, password_confirm: confirm });
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent';

  if (!uid || !token) {
    return (
      <div className="max-w-sm mx-auto mt-8 text-sm text-gray-600">
        This reset link is incomplete. <Link href="/forgot-password" className="text-brand-green font-medium hover:underline">Request a new one</Link>.
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="type-display text-5xl mb-4">Choose a new password</h1>
      {done ? (
        <div className="space-y-3 text-sm">
          <p className="bg-green-50 border border-green-200 text-green-800 rounded-lg px-4 py-3">Password updated. Log in with your new password:</p>
          <div className="flex gap-3">
            {LOGIN_PAGES.map(l => (
              <Link key={l.href} href={l.href} className="text-brand-green font-medium hover:underline">{l.label} log in</Link>
            ))}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">New password</label>
            <input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="new-password" className={inputClass} />
          </div>
          <div>
            <label htmlFor="confirm" className="block text-sm font-medium text-gray-700 mb-1">Confirm new password</label>
            <input id="confirm" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required autoComplete="new-password" className={inputClass} />
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
              {error}{' '}
              {error.includes('expired') && <Link href="/forgot-password" className="font-medium underline">Request a new link</Link>}
            </div>
          )}
          <button type="submit" disabled={loading} className="w-full btn-primary py-2.5 disabled:opacity-60">
            {loading ? 'Saving…' : 'Set new password'}
          </button>
        </form>
      )}
    </div>
  );
}
