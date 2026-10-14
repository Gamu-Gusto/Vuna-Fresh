'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';

export default function FarmerProfilePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ farm_name: '', farm_description: '', farm_location: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/users/me/profile/farmer/')
      .then(p => {
        setForm({
          farm_name: p.farm_name || '',
          farm_description: p.farm_description || '',
          farm_location: p.farm_location || '',
        });
      })
      .catch(err => {
        if (err instanceof ApiError && err.status === 403) {
          router.replace('/farmer/dashboard');
        } else {
          setError('Could not load profile.');
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess(false);
    try {
      await apiClient.patch('/users/me/profile/farmer/', form);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Farm profile</h1>

      <div className="bg-white rounded border border-hairline p-5 text-sm space-y-2">
        <p className="text-gray-500">
          Account email: <span className="text-gray-800 font-medium">{user?.email}</span>
        </p>
        <p className="text-gray-500">
          Name: <span className="text-gray-800 font-medium">{user?.first_name} {user?.last_name}</span>
        </p>
        <p className="text-gray-500">
          Phone: <span className="text-gray-800">{user?.phone || '—'}</span>
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
          Profile updated successfully.
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-5">
        <h2 className="font-semibold text-gray-800">Farm details</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Farm name</label>
          <input
            name="farm_name"
            value={form.farm_name}
            onChange={handleChange}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <input
            name="farm_location"
            value={form.farm_location}
            onChange={handleChange}
            placeholder="e.g. Stellenbosch, Western Cape"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">About your farm</label>
          <textarea
            name="farm_description"
            value={form.farm_description}
            onChange={handleChange}
            rows={4}
            placeholder="Tell buyers about your farm, your growing practices, what makes your produce special…"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="btn-primary px-5 py-2"
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>

      <p className="text-sm text-gray-500">
        Manage marketing consent and your personal data on the{' '}
        <Link href="/farmer/privacy" className="text-brand-green font-medium hover:underline">Privacy</Link> page.
      </p>
    </div>
  );
}
