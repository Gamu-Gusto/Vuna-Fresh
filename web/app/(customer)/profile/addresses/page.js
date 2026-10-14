'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import Link from 'next/link';
import Spinner from '@/components/Spinner';

const emptyForm = {
  label: '', street_address: '', suburb: '', city: '',
  province: '', postal_code: '', country: 'South Africa', is_default: false,
};

export default function AddressesPage() {
  const { user } = useAuth();
  const [addresses, setAddresses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchAddresses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get('/users/me/addresses/');
      setAddresses(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) fetchAddresses();
  }, [user, fetchAddresses]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await apiClient.post('/users/me/addresses/', form);
      setForm(emptyForm);
      setShowForm(false);
      await fetchAddresses();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    setError('');
    try {
      await apiClient.delete(`/users/me/addresses/${id}/`);
      await fetchAddresses();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!user) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Please log in to manage your addresses.</p>
        <Link href="/login" className="text-brand-green font-medium hover:underline">Log in</Link>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Your addresses</h1>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <Spinner />
      ) : (
        <div className="space-y-3 mb-6">
          {addresses.length === 0 && (
            <p className="text-sm text-gray-400">No addresses saved yet.</p>
          )}
          {addresses.map(addr => (
            <div key={addr.id} className="bg-white rounded border border-hairline p-4 flex items-start justify-between">
              <div className="text-sm text-gray-700">
                {addr.label && <p className="font-medium text-gray-800">{addr.label}</p>}
                <p>{addr.street_address}{addr.suburb && `, ${addr.suburb}`}</p>
                <p>{addr.city}, {addr.province} {addr.postal_code}</p>
                {addr.is_default && (
                  <span className="inline-block mt-1 text-xs text-brand-green font-medium">Default</span>
                )}
              </div>
              <button
                onClick={() => handleDelete(addr.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {showForm ? (
        <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Label (optional)" name="label" value={form.label} onChange={handleChange} />
            <Field label="Street address" name="street_address" value={form.street_address} onChange={handleChange} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Suburb (optional)" name="suburb" value={form.suburb} onChange={handleChange} />
            <Field label="City" name="city" value={form.city} onChange={handleChange} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Province" name="province" value={form.province} onChange={handleChange} required />
            <Field label="Postal code" name="postal_code" value={form.postal_code} onChange={handleChange} required />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" name="is_default" checked={form.is_default} onChange={handleChange} />
            Set as default address
          </label>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 btn-primary py-2.5"
            >
              {saving ? 'Saving…' : 'Save address'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setForm(emptyForm); }}
              className="px-4 py-2.5 text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="w-full border border-dashed border-gray-300 rounded-lg py-3 text-sm text-gray-500 hover:border-brand-green hover:text-brand-green transition-colors"
        >
          + Add a new address
        </button>
      )}
    </div>
  );
}

function Field({ label, name, value, onChange, required }) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        id={name} name={name} value={value} onChange={onChange} required={required}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
    </div>
  );
}
