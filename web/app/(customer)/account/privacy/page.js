'use client';

import RequireLogin from '@/components/RequireLogin';
import PrivacySettings from '@/components/PrivacySettings';

export default function BuyerPrivacyPage() {
  return (
    <RequireLogin message="Please log in to manage your privacy settings.">
      <PrivacySettings />
    </RequireLogin>
  );
}
