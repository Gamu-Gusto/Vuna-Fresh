'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

const ROWS = 7;

// The homepage's one loud element: a market-stall price board listing real
// produce and prices from the farms, straight from the products API.
export default function HarvestBoard() {
  const [products, setProducts] = useState(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    apiClient.get('/products/')
      .then(data => {
        setProducts((data.results ?? data).slice(0, ROWS));
        setTotal(data.count ?? (data.results ?? data).length);
      })
      .catch(() => setProducts([]));
  }, []);

  return (
    <div className="min-w-0 rounded-lg bg-[#132849] p-5 sm:p-7">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-white/15 pb-3">
        <h2 className="type-display text-white text-3xl sm:text-4xl">On the board this week</h2>
        <span className="text-xs text-gray-400">Prices set by the farms</span>
      </div>

      {products === null ? (
        <ul aria-hidden="true" className="divide-y divide-white/10">
          {Array.from({ length: 4 }).map((_, i) => (
            <li key={i} className="py-4"><div className="h-5 w-2/3 rounded bg-white/10" /></li>
          ))}
        </ul>
      ) : products.length === 0 ? (
        <p className="py-8 text-gray-300">
          Farms are adding this week&apos;s produce. Create an account and we&apos;ll be ready when you are.
        </p>
      ) : (
        <ul className="divide-y divide-white/10">
          {products.map(p => (
            <li key={p.id}>
              <Link href={`/products/${p.id}`} className="group flex items-baseline gap-4 py-3.5">
                <span className="min-w-0 flex-1">
                  <span className="block text-lg sm:text-xl font-semibold text-white group-hover:text-sprout transition-colors truncate">{p.name}</span>
                  <span className="block text-sm text-gray-400 truncate">{p.farm_name}</span>
                </span>
                <span className="type-display text-maize text-3xl sm:text-4xl font-mono shrink-0">
                  R{Number(p.price).toFixed(2)}
                </span>
                <span className="text-sm text-gray-400 shrink-0 whitespace-nowrap">per {p.unit}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Link href="/products" className="mt-4 inline-block text-sm font-semibold text-sprout hover:text-white">
        {total > ROWS ? `See all ${total} items` : 'Browse the shop'}
      </Link>
    </div>
  );
}
