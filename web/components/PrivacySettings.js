'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import Spinner from './Spinner';
import ErrorMessage from './ErrorMessage';

const REQUEST_TYPES = [
  { value: 'access', label: 'Get a copy of my information', hint: 'We’ll send you everything we hold about you.' },
  { value: 'portability', label: 'Export my information', hint: 'A machine-readable copy you can take elsewhere.' },
  { value: 'deletion', label: 'Delete my account and information', hint: 'We keep only what the law requires (e.g. invoices).' },
];

const REQUEST_STATUS = {
  pending: 'text-amber-700',
  completed: 'text-brand-green',
  denied: 'text-ember',
};

// Shared by the buyer, farmer and driver "Privacy" pages (POPIA rights).
export default function PrivacySettings() {
  const [consents, setConsents] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    Promise.all([apiClient.get('/privacy/consent/'), apiClient.get('/privacy/data-requests/')])
      .then(([c, r]) => {
        setConsents(c.results ?? c);
        setRequests(r.results ?? r);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const marketing = consents.find(c => c.consent_type === 'marketing')?.granted ?? false;
  const dataCollection = consents.find(c => c.consent_type === 'data_collection');

  async function toggleMarketing() {
    setActionError('');
    setSaving('marketing');
    try {
      const [updated] = await apiClient.post('/privacy/consent/update/', [
        { consent_type: 'marketing', granted: !marketing },
      ]);
      setConsents(cs => [...cs.filter(c => c.consent_type !== 'marketing'), updated]);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSaving('');
    }
  }

  async function submitRequest(type) {
    if (type === 'deletion' && !window.confirm('Request deletion of your account and personal information? This can’t be undone once processed.')) return;
    setActionError('');
    setSaving(type);
    try {
      const created = await apiClient.post('/privacy/data-requests/', { request_type: type });
      setRequests(rs => [created, ...rs]);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSaving('');
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Privacy</h1>
        <p className="text-sm text-gray-500 mt-1">
          Control how we use your information. See our{' '}
          <Link href="/privacy" target="_blank" className="text-brand-green font-medium hover:underline">privacy policy</Link>.
        </p>
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{actionError}</div>
      )}

      <section className="bg-white rounded border border-hairline p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Consent</h2>
        <div className="flex items-start justify-between gap-4 text-sm">
          <div>
            <p className="font-medium text-gray-800">Account and order processing</p>
            <p className="text-gray-500">
              Required to use Vuna Fresh.
              {dataCollection?.granted_at && <> Given on {new Date(dataCollection.granted_at).toLocaleDateString('en-ZA')}.</>}
            </p>
          </div>
          <span className="text-xs font-semibold text-brand-green shrink-0">{dataCollection?.granted ? 'Given' : 'Not recorded'}</span>
        </div>
        <div className="flex items-start justify-between gap-4 text-sm border-t border-hairline pt-4">
          <div>
            <p className="font-medium text-gray-800">Specials and seasonal news</p>
            <p className="text-gray-500">Marketing messages from Vuna Fresh.</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={marketing}
            onClick={toggleMarketing}
            disabled={saving === 'marketing'}
            className={`relative w-11 h-6 rounded-full transition-colors shrink-0 disabled:opacity-60 ${marketing ? 'bg-brand-green' : 'bg-gray-300'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${marketing ? 'translate-x-5' : ''}`} />
            <span className="sr-only">Marketing messages</span>
          </button>
        </div>
      </section>

      <section className="bg-white rounded border border-hairline p-5">
        <h2 className="font-semibold text-gray-800 mb-1">Your information</h2>
        <p className="text-sm text-gray-500 mb-4">We respond to requests within 30 days.</p>
        <div className="space-y-3">
          {REQUEST_TYPES.map(({ value, label, hint }) => {
            const pending = requests.some(r => r.request_type === value && r.status === 'pending');
            return (
              <div key={value} className="flex items-center justify-between gap-4 text-sm">
                <div>
                  <p className="font-medium text-gray-800">{label}</p>
                  <p className="text-gray-500">{hint}</p>
                </div>
                <button
                  type="button"
                  onClick={() => submitRequest(value)}
                  disabled={pending || saving === value}
                  className={`shrink-0 text-sm font-semibold px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-60 ${
                    value === 'deletion'
                      ? 'text-red-600 border-red-200 hover:bg-red-50'
                      : 'text-brand-green border-brand-green/30 hover:bg-brand-green/5'
                  }`}
                >
                  {pending ? 'Requested' : saving === value ? 'Sending…' : 'Request'}
                </button>
              </div>
            );
          })}
        </div>

        {requests.length > 0 && (
          <div className="mt-5 border-t border-hairline pt-4">
            <h3 className="text-sm font-semibold text-gray-600 mb-2">Your requests</h3>
            <ul className="text-sm divide-y divide-hairline">
              {requests.map(r => (
                <li key={r.id} className="flex justify-between py-2">
                  <span className="text-gray-700 capitalize">
                    {r.request_type} <span className="text-gray-400">· {new Date(r.requested_at).toLocaleDateString('en-ZA')}</span>
                  </span>
                  <span className={`font-medium capitalize ${REQUEST_STATUS[r.status] ?? 'text-gray-600'}`}>{r.status}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
