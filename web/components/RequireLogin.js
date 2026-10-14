'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import Spinner from './Spinner';

// Buyer pages share a layout with public pages (products, privacy policy), so
// pages that need an account wrap themselves in this instead of a layout guard.
export default function RequireLogin({ children, message = 'Please log in to continue.' }) {
  const { user, loading } = useAuth();

  if (loading) return <Spinner />;
  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">{message}</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }
  return children;
}
