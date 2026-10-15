'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import AuthHeader from '@/components/AuthHeader';
import DashboardShell from '@/components/dashboard/DashboardShell';

const PUBLIC_PATHS = ['/driver/login', '/driver/signup'];

const SECTIONS = [
  {
    label: 'Menu',
    items: [
      { href: '/driver/dashboard', label: 'Deliveries', icon: 'truck', match: ['/driver/deliveries'] },
      { href: '/driver/documents', label: 'Documents', icon: 'receipt' },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/driver/support', label: 'Support', icon: 'chat' },
      { href: '/driver/privacy', label: 'Privacy', icon: 'shield' },
    ],
  },
];

const SHORTCUTS = [
  { href: '/driver/notifications', label: 'Notifications', icon: 'bell' },
];

export default function DriverLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (loading) return;
    if (!isPublic && !user) {
      router.replace('/driver/login');
      return;
    }
    if (!isPublic && user && user.role !== 'driver') {
      router.replace('/');
    }
  }, [loading, user, isPublic, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  if (isPublic) {
    return (
      <div className="min-h-screen flex flex-col bg-brand-bg">
        <AuthHeader />
        <main className="flex-1">{children}</main>
      </div>
    );
  }

  if (!user || user.role !== 'driver') return null;

  return (
    <DashboardShell
      sections={SECTIONS}
      shortcuts={SHORTCUTS}
      notificationsHref="/driver/notifications"
      supportHref="/driver/support"
      loginHref="/driver/login"
      roleLabel="Driver"
    >
      {children}
    </DashboardShell>
  );
}
