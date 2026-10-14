'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import StatusText from '@/components/StatusText';
import { useSearchParams, useRouter } from 'next/navigation';

const ROLES = ['', 'customer', 'farmer', 'driver', 'admin'];
const STATUSES = ['', 'pending', 'active', 'suspended', 'deactivated'];

const ROLE_LABELS = { customer: 'Buyer', farmer: 'Farmer', driver: 'Driver', admin: 'Admin' };
const STATUS_TONES = { pending: 'action', active: 'normal', suspended: 'problem', deactivated: 'quiet' };
const STATUS_LABELS = { pending: 'Waiting for approval', active: 'Active', suspended: 'Suspended', deactivated: 'Deactivated' };

// useSearchParams() needs a Suspense boundary or the production build fails to prerender.
export default function UsersPage() {
  return (
    <Suspense>
      <UsersPageContent />
    </Suspense>
  );
}

function UsersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [role, setRole] = useState(searchParams.get('role') ?? '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') ?? '');
  const [users, setUsers] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [confirmDeactivate, setConfirmDeactivate] = useState(null); // user object
  const [deactivating, setDeactivating] = useState(false);
  const [actionError, setActionError] = useState('');

  const fetchUsers = useCallback(async (roleVal, statusVal) => {
    setLoading(true);
    setActionError('');
    try {
      const params = new URLSearchParams({ page_size: '100' });
      if (roleVal) params.set('role', roleVal);
      if (statusVal) params.set('status', statusVal);
      const data = await apiClient.get(`/admin/users/?${params}`);
      setUsers(data.results ?? []);
      setTotalCount(data.count ?? 0);
    } catch {
      setActionError('Could not load users.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers(role, statusFilter);
  }, [role, statusFilter, fetchUsers]);

  function handleRoleChange(e) {
    setRole(e.target.value);
  }

  function handleStatusChange(e) {
    setStatusFilter(e.target.value);
  }

  async function handleDeactivate() {
    if (!confirmDeactivate) return;
    setDeactivating(true);
    setActionError('');
    try {
      const updated = await apiClient.post(`/admin/users/${confirmDeactivate.id}/deactivate/`);
      setUsers(us => us.map(u => u.id === updated.id ? updated : u));
      setConfirmDeactivate(null);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          {!loading && (
            <p className="text-sm text-gray-500 mt-1">
              {totalCount} user{totalCount !== 1 ? 's' : ''} found
            </p>
          )}
        </div>

        <div className="flex gap-3">
          <select
            value={role}
            onChange={handleRoleChange}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green"
          >
            <option value="">All roles</option>
            {ROLES.filter(Boolean).map(r => (
              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={handleStatusChange}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green"
          >
            <option value="">All statuses</option>
            {STATUSES.filter(Boolean).map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {actionError}
        </div>
      )}

      {/* Deactivation confirmation */}
      {confirmDeactivate && (
        <div className="bg-orange-50 border border-orange-200 rounded p-4">
          <p className="text-sm text-orange-800 font-medium mb-1">
            Deactivate {confirmDeactivate.full_name || confirmDeactivate.email}?
          </p>
          <p className="text-xs text-orange-600 mb-3">
            This will prevent them from logging in. Their data is kept; this doesn&apos;t delete the account.
            You can restore access by updating their status in Django admin.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDeactivate}
              disabled={deactivating}
              className="bg-orange-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-60"
            >
              {deactivating ? 'Deactivating…' : 'Yes, deactivate account'}
            </button>
            <button
              onClick={() => setConfirmDeactivate(null)}
              disabled={deactivating}
              className="text-sm text-gray-500 hover:text-gray-700 px-4 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 text-sm">Loading…</div>
      ) : users.length === 0 ? (
        <div className="bg-white rounded border border-hairline p-12 text-center text-gray-400 text-sm">
          No users match these filters.
        </div>
      ) : (
        <div className="bg-white rounded border border-hairline overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hairline text-left text-xs font-semibold text-gray-500">
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Joined</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {users.map(u => (
                <tr key={u.id} className={u.status === 'deactivated' ? 'opacity-50' : ''}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{u.full_name || '—'}</p>
                    <p className="text-xs text-gray-400">{u.email}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{u.role}</td>
                  <td className="px-4 py-3">
<StatusText label={STATUS_LABELS[u.status] ?? u.status} tone={STATUS_TONES[u.status]} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(u.date_joined).toLocaleDateString('en-ZA')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.status !== 'deactivated' && (
                      <button
                        onClick={() => setConfirmDeactivate(u)}
                        className="text-xs text-gray-500 hover:text-ember hover:underline"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
