'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import ApplicationStatusScreen from '@/components/ApplicationStatusScreen';

export default function FarmerPendingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const p = await apiClient.get('/users/me/profile/farmer/');
        if (p.is_approved) {
          router.replace('/farmer/dashboard');
          return;
        }
        setProfile(p);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;
  if (!profile) return null;

  return (
    <ApplicationStatusScreen
      status={profile.rejection_reason ? 'rejected' : 'pending'}
      applicantLabel="farmer"
      reason={profile.rejection_reason}
      email={user?.email}
    />
  );
}
