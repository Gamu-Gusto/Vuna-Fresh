'use client';

import RequireLogin from '@/components/RequireLogin';
import NotificationsInbox from '@/components/NotificationsInbox';

export default function BuyerNotificationsPage() {
  return (
    <RequireLogin message="Please log in to see your notifications.">
      <NotificationsInbox />
    </RequireLogin>
  );
}
