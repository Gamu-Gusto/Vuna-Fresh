'use client';

import { useParams } from 'next/navigation';
import { SupportThread } from '@/components/SupportCenter';

export default function AdminSupportThreadPage() {
  const { id } = useParams();
  return <SupportThread id={id} backHref="/admin/support" admin />;
}
