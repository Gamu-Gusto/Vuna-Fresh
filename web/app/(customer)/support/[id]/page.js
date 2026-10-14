'use client';

import { useParams } from 'next/navigation';
import RequireLogin from '@/components/RequireLogin';
import { SupportThread } from '@/components/SupportCenter';

export default function BuyerSupportThreadPage() {
  const { id } = useParams();
  return (
    <RequireLogin message="Please log in to view this issue.">
      <SupportThread id={id} backHref="/support" />
    </RequireLogin>
  );
}
