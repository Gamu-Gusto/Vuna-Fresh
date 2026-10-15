'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import AuthHeader from '@/components/AuthHeader';
import DashboardShell from '@/components/dashboard/DashboardShell';

const PUBLIC_PATHS = ['/admin/login'];

const SECTIONS = [
  {
    label: 'Overview',
    items: [
      { href: '/admin/dashboard', label: 'Dashboard', icon: 'home' },
      { href: '/admin/orders', label: 'Orders', icon: 'basket' },
    ],
  },
  {
    label: 'Money',
    items: [
      { href: '/admin/payments', label: 'Payments to verify', icon: 'banknote' },
      { href: '/admin/payouts', label: 'Farmer payouts', icon: 'wallet' },
      { href: '/admin/invoices', label: 'Invoices', icon: 'receipt' },
    ],
  },
  {
    label: 'People',
    items: [
      { href: '/admin/approvals', label: 'Approvals', icon: 'check' },
      { href: '/admin/users', label: 'Users', icon: 'users' },
      { href: '/admin/support', label: 'Support', icon: 'chat' },
      { href: '/admin/privacy', label: 'Privacy requests', icon: 'shield' },
    ],
  },
];

const SHORTCUTS = [
  { href: '/admin/notifications', label: 'Notifications', icon: 'bell' },
];

export default function AdminLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    if (loading) return;
    if (!isPublic && !user) {
      router.replace('/admin/login');
      return;
    }
    if (!isPublic && user && user.role !== 'admin') {
      router.replace('/');
    }
  }, [loading, user, isPublic, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-400 text-sm">Loading…</p>
      </div>
    );
  }

  if (isPublic) {
    return (
      <div className="min-h-screen flex flex-col bg-gray-50">
        <AuthHeader />
        <main className="flex-1">{children}</main>
      </div>
    );
  }

  if (!user || user.role !== 'admin') return null;

  return (
    <DashboardShell
      sections={SECTIONS}
      shortcuts={SHORTCUTS}
      notificationsHref="/admin/notifications"
      supportHref="/admin/support"
      loginHref="/admin/login"
      roleLabel="Admin"
    >
      {children}
    </DashboardShell>
  );
}
