'use client';

import { useState, useEffect, useCallback } from 'react';
import StatusText from '@/components/StatusText';
import { apiClient, ApiError } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import EmptyState from '@/components/EmptyState';

export default function InventoryPage() {
  const router = useRouter();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadProducts = useCallback(async (farmerId) => {
    const data = await apiClient.get(`/products/?farmer=${farmerId}&page_size=100`);
    setProducts(data.results ?? []);
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const profile = await apiClient.get('/users/me/profile/farmer/');
        await loadProducts(profile.id);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          router.replace('/farmer/dashboard');
        } else {
          setError('Could not load inventory. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [router, loadProducts]);

  async function handleDelete(id) {
    if (!confirm('Delete this product? This cannot be undone.')) return;
    try {
      await apiClient.delete(`/products/${id}/`);
      setProducts(ps => ps.filter(p => p.id !== id));
    } catch {
      alert('Could not delete product. Please try again.');
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Inventory</h1>
        <Link
          href="/farmer/inventory/new"
          className="btn-primary text-sm px-4 py-2"
        >
          + Add product
        </Link>
      </div>

      {products.length === 0 ? (
        <EmptyState className="p-12">
          <span className="block">You haven&apos;t added any products yet.</span>
          <Link
            href="/farmer/inventory/new"
            className="mt-4 inline-block btn-primary text-sm px-4 py-2"
          >
            Add your first product
          </Link>
        </EmptyState>
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hairline text-left text-xs font-semibold text-gray-500">
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {products.map(product => {
                const lowStock = product.stock_quantity <= product.low_stock_threshold;
                return (
                  <tr key={product.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{product.name}</p>
                      <p className="text-xs text-gray-400">{product.unit}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-700 font-mono">
                      R{Number(product.price).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-medium font-mono ${lowStock ? 'text-amber-800' : 'text-gray-700'}`}>
                        {product.stock_quantity}
                      </span>
                      {lowStock && ( <span className="ml-1 text-xs font-medium text-amber-800">(running low)</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {product.is_available ? (
                        <StatusText label="On sale" />
                      ) : (
                        <StatusText label="Hidden from buyers" tone="quiet" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-4">
                        <Link
                          href={`/farmer/inventory/${product.id}`}
                          className="text-brand-green hover:underline text-xs font-medium"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => handleDelete(product.id)}
                          className="text-red-400 hover:text-red-600 text-xs font-medium"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
