'use client';

import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ApplicationStatusScreen from '@/components/ApplicationStatusScreen';

export default function BusinessPendingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    async function load() {
      try {
        const d = await apiClient.get('/buyers/me/business/');
        if (d.approval_status === 'active') {
          router.replace('/products');
          return;
        }
        setDetails(d);
      } catch (err) {
        // Not a business buyer at all — nothing to show here.
        if (err instanceof ApiError) router.replace('/products');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user, router]);

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to view your application status.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (!details) return null;

  return (
    <ApplicationStatusScreen
      status={details.approval_status === 'suspended' ? 'suspended' : 'pending'}
      applicantLabel="business buyer"
      reason={details.rejection_reason}
      email={user?.email}
    />
  );
}
