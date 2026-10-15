'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import AuthHeader from '@/components/AuthHeader';
import DashboardShell from '@/components/dashboard/DashboardShell';

const PUBLIC_PATHS = ['/farmer/login', '/farmer/signup'];

const SECTIONS = [
  {
    label: 'Menu',
    items: [
      { href: '/farmer/dashboard', label: 'Dashboard', icon: 'home' },
      { href: '/farmer/inventory', label: 'Products', icon: 'sprout' },
      { href: '/farmer/orders', label: 'Orders', icon: 'basket' },
      { href: '/farmer/payouts', label: 'Payouts', icon: 'wallet' },
      { href: '/farmer/reviews', label: 'Reviews', icon: 'star' },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/farmer/profile', label: 'Farm profile', icon: 'user' },
      { href: '/farmer/support', label: 'Support', icon: 'chat' },
      { href: '/farmer/privacy', label: 'Privacy', icon: 'shield' },
    ],
  },
];

const SHORTCUTS = [
  { href: '/farmer/inventory/new', label: 'Add a product', icon: 'plus' },
  { href: '/farmer/notifications', label: 'Notifications', icon: 'bell' },
];

export default function FarmerLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (loading) return;
    if (!isPublic && !user) {
      router.replace('/farmer/login');
      return;
    }
    if (!isPublic && user && user.role !== 'farmer') {
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

  if (!user || user.role !== 'farmer') return null;

  return (
    <DashboardShell
      sections={SECTIONS}
      shortcuts={SHORTCUTS}
      notificationsHref="/farmer/notifications"
      supportHref="/farmer/support"
      loginHref="/farmer/login"
      roleLabel="Farmer"
    >
      {children}
    </DashboardShell>
  );
}
