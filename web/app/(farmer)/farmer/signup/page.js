'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Farmer signup is now part of the single unified signup flow at /signup.
// This route is kept (rather than removed) so existing links/bookmarks
// still land somewhere sensible, with the Farmer role pre-selected.
export default function FarmerSignupRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/signup?role=farmer');
  }, [router]);

  return null;
}
