'use client';

import { useState, useEffect, useCallback } from 'react';
import StatusText from '@/components/StatusText';
import { apiClient, ApiError } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import EmptyState from '@/components/EmptyState';

// "Remove" takes a product off the shop. One that has been ordered is archived
// (kept with its orders, payouts and reviews, and can be restored); one that
// never was is deleted. Either way carts and subscriptions are cleared and
// subscribed buyers are told (backend: products/archiving.py).

export default function InventoryPage() {
  const router = useRouter();
  const [farmerId, setFarmerId] = useState(null);
  const [tab, setTab] = useState('active'); // active | archived
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null); // { text, href?, linkText? }
  const [busy, setBusy] = useState(null);

  const loadProducts = useCallback(async (id, which) => {
    const archived = which === 'archived' ? '&archived=true' : '';
    const data = await apiClient.get(`/products/?farmer=${id}${archived}`);
    setProducts(data.results ?? []);
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const profile = await apiClient.get('/users/me/profile/farmer/');
        setFarmerId(profile.id);
        await loadProducts(profile.id, 'active');
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          router.replace('/farmer/dashboard');
        } else {
          setError('Could not load your products. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [router, loadProducts]);

  async function switchTab(next) {
    if (next === tab) return;
    setTab(next);
    setNotice(null);
    setLoading(true);
    try {
      await loadProducts(farmerId, next);
    } catch {
      setError('Could not load your products. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove(product) {
    if (!window.confirm(
      `Remove ${product.name}?\n\nIt comes off the shop straight away, and any buyers subscribed to it are told their `
      + 'subscription has ended.\n\nIf it has been ordered before, it moves to Archived so you can restore it next '
      + 'season. If it never has, it’s deleted.',
    )) return;
    setBusy(product.id);
    setNotice(null);
    try {
      const { result } = await apiClient.delete(`/products/${product.id}/`);
      setProducts(ps => ps.filter(p => p.id !== product.id));
      setNotice(result === 'archived'
        ? { text: `${product.name} moved to Archived. Its orders and reviews are kept.` }
        : { text: `${product.name} deleted.` });
    } catch (err) {
      setNotice({ text: `Could not remove ${product.name}: ${err.message}`, error: true });
    } finally {
      setBusy(null);
    }
  }

  async function handleRestore(product) {
    setBusy(product.id);
    setNotice(null);
    try {
      await apiClient.post(`/products/${product.id}/restore/`);
      setProducts(ps => ps.filter(p => p.id !== product.id));
      setNotice({
        text: `${product.name} is back on your list, hidden from buyers. Update the stock and price, then tick "List as available".`,
        href: `/farmer/inventory/${product.id}`,
        linkText: 'Edit it now',
      });
    } catch (err) {
      setNotice({ text: `Could not restore ${product.name}: ${err.message}`, error: true });
    } finally {
      setBusy(null);
    }
  }

  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Products</h1>
        <Link href="/farmer/inventory/new" className="btn-primary text-sm px-4 py-2">
          + Add product
        </Link>
      </div>

      <div role="tablist" aria-label="Products" className="inline-flex rounded-full bg-white border border-hairline p-1 text-sm">
        {[['active', 'Your products'], ['archived', 'Archived']].map(([value, label]) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            onClick={() => switchTab(value)}
            className={`rounded-full px-4 py-1.5 font-medium transition-colors ${tab === value ? 'bg-leaf text-navy' : 'text-gray-500 hover:text-navy'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {notice && (
        <div
          role="status"
          className={`rounded-lg px-4 py-3 text-sm border ${notice.error ? 'bg-red-50 border-red-200 text-red-700' : 'bg-leaf border-brand-green/20 text-navy'}`}
        >
          {notice.text}
          {notice.href && (
            <> <Link href={notice.href} className="font-semibold text-brand-green hover:underline">{notice.linkText}</Link></>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>
      ) : products.length === 0 ? (
        tab === 'active' ? (
          <EmptyState className="p-12">
            <span className="block">You haven&apos;t added any products yet.</span>
            <Link href="/farmer/inventory/new" className="mt-4 inline-block btn-primary text-sm px-4 py-2">
              Add your first product
            </Link>
          </EmptyState>
        ) : (
          <EmptyState className="p-12">
            Nothing archived. Products you remove after they&apos;ve been ordered land here, ready to restore next season.
          </EmptyState>
        )
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hairline text-left text-xs font-semibold text-gray-500">
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">{tab === 'active' ? 'Stock' : 'Archived on'}</th>
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
                      {tab === 'active' ? (
                        <>
                          <span className={`font-medium font-mono ${lowStock ? 'text-amber-800' : 'text-gray-700'}`}>
                            {product.stock_quantity}
                          </span>
                          {lowStock && <span className="ml-1 text-xs font-medium text-amber-800">(running low)</span>}
                        </>
                      ) : (
                        <span className="text-gray-600">
                          {product.archived_at ? new Date(product.archived_at).toLocaleDateString('en-ZA') : '—'}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {tab === 'archived' ? (
                        <StatusText label="Archived" tone="quiet" />
                      ) : product.is_available ? (
                        <StatusText label="On sale" />
                      ) : (
                        <StatusText label="Hidden from buyers" tone="quiet" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-4">
                        {tab === 'active' ? (
                          <>
                            <Link href={`/farmer/inventory/${product.id}`} className="text-brand-green hover:underline text-xs font-medium">
                              Edit
                            </Link>
                            <button
                              onClick={() => handleRemove(product)}
                              disabled={busy === product.id}
                              className="text-red-500 hover:text-red-700 text-xs font-medium disabled:opacity-60"
                            >
                              Remove
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleRestore(product)}
                            disabled={busy === product.id}
                            className="text-brand-green hover:underline text-xs font-semibold disabled:opacity-60"
                          >
                            {busy === product.id ? 'Restoring…' : 'Restore'}
                          </button>
                        )}
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
