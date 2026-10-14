'use client';

import Link from 'next/link';
import Logo from './Logo';
import { useAuth } from '@/lib/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import NotificationBell from './NotificationBell';

export default function FarmerNav() {
  const { logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  async function handleLogout() {
    await logout();
    router.push('/farmer/login');
  }

  return (
    <nav className="bg-navy">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-6">
        <Link href="/farmer/dashboard" className="flex items-center">
          <Logo />
        </Link>
        <div className="flex items-center gap-6 text-sm font-medium overflow-x-auto whitespace-nowrap">
          <NavLink href="/farmer/dashboard" pathname={pathname}>Dashboard</NavLink>
          <NavLink href="/farmer/inventory" pathname={pathname}>Inventory</NavLink>
          <NavLink href="/farmer/orders" pathname={pathname}>Orders</NavLink>
          <NavLink href="/farmer/payouts" pathname={pathname}>Payouts</NavLink>
          <NavLink href="/farmer/reviews" pathname={pathname}>Reviews</NavLink>
          <NavLink href="/farmer/support" pathname={pathname}>Support</NavLink>
          <NavLink href="/farmer/profile" pathname={pathname}>Profile</NavLink>
          <NotificationBell
            href="/farmer/notifications"
            className={pathname.startsWith('/farmer/notifications') ? 'text-sprout' : 'text-gray-300 hover:text-sprout'}
          />
          <button onClick={handleLogout} className="text-gray-300 hover:text-sprout transition-colors">
            Log out
          </button>
        </div>
      </div>
    </nav>
  );
}

function NavLink({ href, pathname, children }) {
  const active = pathname === href || (href !== '/farmer/dashboard' && pathname.startsWith(href));
  return (
    <Link
      href={href}
      className={`transition-colors hover:text-sprout ${active ? 'text-sprout font-semibold' : 'text-gray-300'}`}
    >
      {children}
    </Link>
  );
}
