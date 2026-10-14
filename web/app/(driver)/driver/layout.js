'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import AuthHeader from '@/components/AuthHeader';
import DriverNav from '@/components/DriverNav';

const PUBLIC_PATHS = ['/driver/login', '/driver/signup'];

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
    <div className="min-h-screen flex flex-col">
      <DriverNav />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        {children}
      </main>
      <footer className="text-center text-xs text-gray-400 py-6">
        © 2026 Vuna Fresh. From the farm to your Home.
      </footer>
    </div>
  );
}
