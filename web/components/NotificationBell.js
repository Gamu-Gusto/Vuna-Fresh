'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { apiClient } from '@/lib/api';

// Nav link to the notifications page with an unread count. Re-checks on every
// navigation so the count drops after reading notifications.
export default function NotificationBell({ href, className = '' }) {
  const pathname = usePathname();
  const [count, setCount] = useState(0);

  useEffect(() => {
    apiClient.get('/notifications/unread_count/')
      .then(data => setCount(data.count))
      .catch(() => {});
  }, [pathname]);

  return (
    <Link href={href} className={`inline-flex items-center gap-1 ${className}`} aria-label={`Notifications${count ? ` (${count} unread)` : ''}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-5 h-5" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
      </svg>
      {count > 0 && <span className="text-xs font-semibold">{count > 9 ? '9+' : count}</span>}
    </Link>
  );
}
