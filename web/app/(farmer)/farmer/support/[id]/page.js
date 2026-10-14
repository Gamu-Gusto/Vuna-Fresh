'use client';

import { useParams } from 'next/navigation';
import { SupportThread } from '@/components/SupportCenter';

export default function FarmerSupportThreadPage() {
  const { id } = useParams();
  return <SupportThread id={id} backHref="/farmer/support" />;
}
