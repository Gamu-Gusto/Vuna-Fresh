'use client';

import RequireLogin from '@/components/RequireLogin';
import { SupportList } from '@/components/SupportCenter';

export default function BuyerSupportPage() {
  return (
    <RequireLogin message="Please log in to contact support.">
      <SupportList basePath="/support" />
    </RequireLogin>
  );
}
