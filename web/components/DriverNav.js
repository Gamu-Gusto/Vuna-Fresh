'use client';

import Link from 'next/link';
import Logo from './Logo';
import { useAuth } from '@/lib/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import NotificationBell from './NotificationBell';

export default function DriverNav() {
  const { logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  async function handleLogout() {
    await logout();
    router.push('/driver/login');
  }

  const links = [
    { href: '/driver/dashboard', label: 'Deliveries' },
    { href: '/driver/support', label: 'Support' },
    { href: '/driver/privacy', label: 'Privacy' },
  ];

  return (
    <nav className="bg-navy">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-6">
        <Link href="/driver/dashboard" className="flex items-center">
          <Logo />
        </Link>
        <div className="flex items-center gap-6 text-sm font-medium overflow-x-auto whitespace-nowrap">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`transition-colors hover:text-sprout ${
                pathname === href || pathname.startsWith(href + '/')
                  ? 'text-sprout font-semibold'
                  : 'text-gray-300'
              }`}
            >
              {label}
            </Link>
          ))}
          <NotificationBell
            href="/driver/notifications"
            className={pathname.startsWith('/driver/notifications') ? 'text-sprout' : 'text-gray-300 hover:text-sprout'}
          />
          <button
            onClick={handleLogout}
            className="text-gray-300 hover:text-sprout transition-colors"
          >
            Log out
          </button>
        </div>
      </div>
    </nav>
  );
}
