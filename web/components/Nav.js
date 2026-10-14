'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { useCart } from '@/lib/cart-context';
import Logo from './Logo';
import NotificationBell from './NotificationBell';

const DASHBOARDS = {
  farmer: { href: '/farmer/dashboard', label: 'Farm dashboard' },
  driver: { href: '/driver/dashboard', label: 'My deliveries' },
  admin: { href: '/admin/dashboard', label: 'Admin' },
};

export default function Nav() {
  const { user, logout } = useAuth();
  const { itemCount } = useCart();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the mobile menu after navigating.
  useEffect(() => {
    const close = () => setOpen(false);
    window.addEventListener('popstate', close);
    return () => window.removeEventListener('popstate', close);
  }, []);

  async function handleLogout() {
    setOpen(false);
    await logout();
    router.push('/login');
  }

  // Farmers, drivers and admins can browse the shop but not buy, so they get a
  // way back to their own area instead of buyer links.
  const dashboard = user && user.role !== 'customer' ? DASHBOARDS[user.role] : null;

  const links = dashboard
    ? [
        { href: '/products', label: 'Shop' },
        dashboard,
      ]
    : user
    ? [
        { href: '/products', label: 'Shop' },
        { href: '/orders', label: 'Orders' },
        { href: '/account', label: 'Account' },
      ]
    : [
        { href: '/products', label: 'Shop' },
        { href: '/signup?role=farmer', label: 'Sell your produce' },
        { href: '/login', label: 'Log in' },
      ];

  // Links with a query (e.g. /signup?role=farmer) are shortcuts into another
  // page, so they never show as the current page.
  const linkClass = href =>
    `transition-colors hover:text-white ${!href.includes('?') && pathname === href ? 'text-white' : 'text-gray-300'}`;

  return (
    <nav className="bg-navy text-sm font-medium">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-6">
        <Link href="/" aria-label="Vuna Fresh home" className="shrink-0">
          <Logo />
        </Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-7">
          {links.map(l => (
            <Link key={l.href} href={l.href} className={linkClass(l.href)}>{l.label}</Link>
          ))}
          {user ? (
            <>
              {!dashboard && <NotificationBell href="/notifications" className="text-gray-300 hover:text-white" />}
              {!dashboard && <CartLink count={itemCount} />}
              <button onClick={handleLogout} className="text-gray-300 hover:text-white transition-colors">Log out</button>
            </>
          ) : (
            <Link href="/signup" className="btn-primary px-4 py-2">Create account</Link>
          )}
        </div>

        {/* Mobile: cart stays visible, everything else behind the menu button */}
        <div className="flex md:hidden items-center gap-4">
          {user && !dashboard && <CartLink count={itemCount} />}
          <button
            type="button"
            onClick={() => setOpen(o => !o)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            className="text-gray-200 hover:text-white px-1 py-1"
          >
            {open ? 'Close' : 'Menu'}
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-menu" className="md:hidden border-t border-white/10 px-4 pb-4">
          {links.map(l => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="block py-3 text-base text-gray-100 border-b border-white/10">
              {l.label}
            </Link>
          ))}
          {user ? (
            <>
              {!dashboard && <Link href="/notifications" onClick={() => setOpen(false)} className="block py-3 text-base text-gray-100 border-b border-white/10">Notifications</Link>}
              <button onClick={handleLogout} className="block w-full text-left py-3 text-base text-gray-300">Log out</button>
            </>
          ) : (
            <Link href="/signup" onClick={() => setOpen(false)} className="btn-primary mt-4 block text-center py-3 text-base">Create account</Link>
          )}
        </div>
      )}
    </nav>
  );
}

function CartLink({ count }) {
  return (
    <Link href="/cart" className="text-gray-300 hover:text-white transition-colors">
      Cart{count > 0 && <> ({count})</>}
    </Link>
  );
}
