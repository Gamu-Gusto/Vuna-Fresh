'use client';

import Link from 'next/link';
import Logo from './Logo';
import { useAuth } from '@/lib/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import NotificationBell from './NotificationBell';

const NAV_LINKS = [
  { href: '/admin/dashboard', label: 'Dashboard' },
  { href: '/admin/approvals', label: 'Approvals' },
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/orders', label: 'Orders' },
  { href: '/admin/payments', label: 'Payments' },
  { href: '/admin/payouts', label: 'Payouts' },
  { href: '/admin/invoices', label: 'Invoices' },
  { href: '/admin/support', label: 'Support' },
  { href: '/admin/privacy', label: 'Privacy' },
];

export default function AdminNav() {
  const { logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  async function handleLogout() {
    await logout();
    router.push('/admin/login');
  }

  return (
    <nav className="bg-navy text-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          <Link href="/admin/dashboard" className="flex items-center opacity-90 hover:opacity-100">
            <Logo />
          </Link>
          <span className="text-sm font-semibold text-gray-600st">Admin</span>
          <div className="flex items-center gap-5 text-sm font-medium overflow-x-auto whitespace-nowrap">
            {NAV_LINKS.map(({ href, label }) => {
              const active = pathname === href || (href !== '/admin/dashboard' && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  className={`transition-colors hover:text-white ${active ? 'text-white' : 'text-gray-400'}`}
                >
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-5">
          <NotificationBell href="/admin/notifications" className="text-gray-400 hover:text-white" />
          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Log out
          </button>
        </div>
      </div>
    </nav>
  );
}
