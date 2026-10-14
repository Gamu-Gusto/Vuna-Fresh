'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import RequireLogin from '@/components/RequireLogin';

const SECTIONS = [
  { href: '/orders', title: 'Orders', text: 'Track deliveries and pay for orders.' },
  { href: '/subscriptions', title: 'Subscriptions', text: 'Regular deliveries you can pause or cancel any time.' },
  { href: '/invoices', title: 'Invoices', text: 'Business accounts on credit terms.' },
  { href: '/profile/addresses', title: 'Addresses', text: 'Where we deliver to.' },
  { href: '/notifications', title: 'Notifications', text: 'Updates and email preferences.' },
  { href: '/support', title: 'Help & support', text: 'Report a problem with an order.' },
  { href: '/account/privacy', title: 'Privacy', text: 'Marketing consent and your data.' },
];

export default function AccountPage() {
  return (
    <RequireLogin message="Please log in to see your account.">
      <Account />
    </RequireLogin>
  );
}

function Account() {
  const { user } = useAuth();
  return (
    <div className="max-w-2xl">
      <h1 className="type-display text-5xl">Your account</h1>
      <p className="mt-2 text-gray-600">Signed in as {user.email}</p>
      <ul className="mt-8 border-t border-hairline">
        {SECTIONS.map(s => (
          <li key={s.href} className="border-b border-hairline">
            <Link href={s.href} className="group flex flex-col sm:flex-row sm:items-baseline sm:gap-6 py-4">
              <span className="sm:w-48 shrink-0 font-semibold text-navy group-hover:text-brand-green group-hover:underline underline-offset-4">{s.title}</span>
              <span className="text-gray-600">{s.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
