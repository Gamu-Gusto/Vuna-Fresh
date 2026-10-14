'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';

const TYPE_LABELS = {
  access: 'Copy of their information',
  portability: 'Export of their information',
  deletion: 'Delete account and information',
};

// POPIA data requests from users. Fulfilment (sending the export, deleting the
// account) is done manually; this page tracks it and records the outcome.
export default function AdminPrivacyPage() {
  const [requests, setRequests] = useState([]);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loadedAt, setLoadedAt] = useState(0);

  useEffect(() => {
    apiClient.get('/privacy/data-requests/')
      .then(data => {
        setRequests(data.results ?? data);
        setLoadedAt(Date.now());
      })
      .catch(() => setError('Could not load data requests.'))
      .finally(() => setLoading(false));
  }, []);

  async function resolve(r, status) {
    const verb = status === 'completed' ? 'completed' : 'denied';
    if (!window.confirm(`Mark this ${r.request_type} request from ${r.user_email} as ${verb}?`)) return;
    setError('');
    try {
      const updated = await apiClient.patch(`/privacy/data-requests/${r.id}/`, { status });
      setRequests(rs => rs.map(x => (x.id === r.id ? updated : x)));
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;

  const visible = showAll ? requests : requests.filter(r => r.status === 'pending');

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Privacy requests</h1>
          <p className="text-sm text-gray-500 mt-1">POPIA requires a response within 30 days of each request.</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={showAll} onChange={e => setShowAll(e.target.checked)} /> Show completed
        </label>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>}

      {visible.length === 0 ? (
        <div className="text-gray-600">No open requests.</div>
      ) : (
        <ul className="space-y-3">
          {visible.map(r => {
            const daysOpen = Math.floor((loadedAt - new Date(r.requested_at)) / 86400000);
            return (
              <li key={r.id} className="bg-white rounded border border-hairline p-4 flex flex-wrap items-center justify-between gap-3 text-sm">
                <div>
                  <p className="font-semibold text-gray-900">{TYPE_LABELS[r.request_type] ?? r.request_type}</p>
                  <p className="text-gray-500">{r.user_email}</p>
                  <p className={`text-xs ${r.status === 'pending' && daysOpen >= 21 ? 'text-ember font-semibold' : 'text-gray-400'}`}>
                    Requested {new Date(r.requested_at).toLocaleDateString('en-ZA')}
                    {r.status === 'pending' ? `, open for ${daysOpen} day${daysOpen === 1 ? '' : 's'}` : `, ${r.status}`}
                  </p>
                </div>
                {r.status === 'pending' && (
                  <div className="flex gap-2">
                    <button onClick={() => resolve(r, 'completed')} className="btn-primary text-sm px-3 py-1.5">Mark completed</button>
                    <button onClick={() => resolve(r, 'denied')} className="text-sm font-semibold px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50">Deny</button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
