'use client';

import { useParams } from 'next/navigation';
import { SupportThread } from '@/components/SupportCenter';

export default function DriverSupportThreadPage() {
  const { id } = useParams();
  return <SupportThread id={id} backHref="/driver/support" />;
}
