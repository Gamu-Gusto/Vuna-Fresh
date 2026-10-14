'use client';

import { useEffect } from 'react';
import Link from 'next/link';

// Root error boundary — catches any unhandled error thrown while rendering
// or in an effect anywhere below this (any page, any route group). This is
// the last line of defence for a missed try/catch around an API call: worst
// case the user sees this instead of a blank screen or a dev error overlay.
export default function GlobalError({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-brand-bg px-4 py-16">
      <div className="max-w-xl mx-auto">
        <h1 className="type-display text-5xl">That didn&apos;t work</h1>
        <p className="mt-4 text-gray-700 leading-relaxed">
          {error?.message || 'Something on this page failed to load.'} Try again, and if it keeps happening,{' '}
          <Link href="/support" className="text-brand-green font-semibold underline underline-offset-4">let us know</Link>.
        </p>
        <button onClick={reset} className="btn-primary mt-6 px-6 py-2.5">
          Try again
        </button>
      </div>
    </div>
  );
}
