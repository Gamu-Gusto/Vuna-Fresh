'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import ProductCard from '@/components/ProductCard';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null });

  const fetchCategories = useCallback(async () => {
    try {
      const data = await apiClient.get('/categories/');
      setCategories(data.results ?? data);
    } catch {}
  }, []);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page });
      if (search) params.set('search', search);
      if (categoryFilter) params.set('category', categoryFilter);
      const data = await apiClient.get(`/products/?${params}`);
      setProducts(data.results);
      setPagination({ count: data.count, next: data.next, previous: data.previous });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, page]);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);
  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  return (
    <div>
      <header className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="type-display text-5xl sm:text-6xl">This week&apos;s produce</h1>
          <p className="mt-2 text-gray-600">
            Ordered straight from the farm that grew it. Pay by EFT and we deliver to your door.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 lg:w-[28rem]">
          <label className="sr-only" htmlFor="product-search">Search produce</label>
          <input
            id="product-search"
            type="search"
            placeholder="Search produce"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="flex-1 min-w-0 border border-gray-300 rounded-md px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green"
          />
          <label className="sr-only" htmlFor="product-category">Category</label>
          <select
            id="product-category"
            value={categoryFilter}
            onChange={e => { setCategoryFilter(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded-md px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green bg-white"
          >
            <option value="">All categories</option>
            {categories.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </header>

      {loading && <Spinner />}
      {error && <ErrorMessage message={error} onRetry={fetchProducts} />}

      {!loading && !error && products.length === 0 && (
        <EmptyState className="py-16">
          {search || categoryFilter ? 'Nothing matches that search. Try another word or category.' : 'Farms are still adding this week’s produce. Check back soon.'}
        </EmptyState>
      )}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 min-[480px]:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-10">
            {products.map(p => <ProductCard key={p.id} product={p} />)}
          </div>

          {/* Pagination */}
          {(pagination.next || pagination.previous) && (
            <div className="mt-8 flex justify-center gap-3">
              <button
                onClick={() => setPage(p => p - 1)}
                disabled={!pagination.previous}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-500">Page {page}</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!pagination.next}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
