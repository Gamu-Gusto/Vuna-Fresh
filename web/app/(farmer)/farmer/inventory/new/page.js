'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ProductFormFields } from '@/components/FarmerProductForm';

const EMPTY_FORM = {
  name: '', description: '', price: '', unit: '',
  stock_quantity: '', low_stock_threshold: '10',
  is_available: true, image_url: '', category: '',
};

export default function NewProductPage() {
  const router = useRouter();
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiClient.get('/products/categories/?page_size=100').then(data => {
      setCategories(data.results ?? []);
    });
  }, []);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiClient.post('/products/', {
        ...form,
        price: parseFloat(form.price),
        stock_quantity: parseInt(form.stock_quantity, 10),
        low_stock_threshold: parseInt(form.low_stock_threshold, 10),
        category: parseInt(form.category, 10),
      });
      router.push('/farmer/inventory');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 mb-6 text-sm">
        <Link href="/farmer/inventory" className="text-gray-400 hover:text-gray-600">← Inventory</Link>
        <span className="text-gray-300">/</span>
        <span className="font-semibold text-gray-800">Add product</span>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-5">
        <ProductFormFields form={form} onChange={handleChange} categories={categories} />

        <div className="flex gap-3 pt-2 border-t border-hairline">
          <button
            type="submit"
            disabled={loading}
            className="btn-primary px-5 py-2"
          >
            {loading ? 'Saving…' : 'Save product'}
          </button>
          <Link
            href="/farmer/inventory"
            className="px-5 py-2 rounded-lg border border-hairline text-gray-600 text-sm hover:bg-gray-50 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
