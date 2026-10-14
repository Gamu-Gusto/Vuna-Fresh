'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import Spinner from './Spinner';
import ErrorMessage from './ErrorMessage';
import EmptyState from './EmptyState';

const CATEGORY_LABELS = {
  order_updates: 'Order updates',
  issue_updates: 'Support updates',
};
const CHANNEL_LABELS = { email: 'Email', sms: 'SMS', push: 'Push' };
// SMS and push aren't connected yet, so only email preferences are shown.
// Marketing is governed by the marketing consent on the Privacy page instead.
const VISIBLE_CHANNELS = ['email'];
const HIDDEN_CATEGORIES = ['marketing'];

// Shared by every role's notifications page.
export default function NotificationsInbox() {
  const [notifications, setNotifications] = useState([]);
  const [next, setNext] = useState(null);
  const [prefs, setPrefs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    Promise.all([apiClient.get('/notifications/'), apiClient.get('/notifications/preferences/')])
      .then(([n, p]) => {
        setNotifications(n.results ?? n);
        setNext(n.next ?? null);
        setPrefs(p);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function loadMore() {
    const page = new URL(next).searchParams.get('page');
    const n = await apiClient.get(`/notifications/?page=${page}`);
    setNotifications(ns => [...ns, ...n.results]);
    setNext(n.next);
  }

  async function markRead(id) {
    setNotifications(ns => ns.map(n => (n.id === id ? { ...n, read: true } : n)));
    apiClient.post(`/notifications/${id}/mark_read/`).catch(() => {});
  }

  async function markAllRead() {
    setActionError('');
    try {
      await apiClient.post('/notifications/mark_all_read/');
      setNotifications(ns => ns.map(n => ({ ...n, read: true })));
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function togglePref(pref) {
    setActionError('');
    try {
      const [updated] = await apiClient.post('/notifications/preferences/update/', [
        { channel: pref.channel, category: pref.category, enabled: !pref.enabled },
      ]);
      setPrefs(ps => ps.map(p => (p.id === updated.id ? updated : p)));
    } catch (err) {
      setActionError(err.message);
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} onRetry={() => window.location.reload()} />;

  const hasUnread = notifications.some(n => !n.read);
  const visiblePrefs = prefs.filter(p => VISIBLE_CHANNELS.includes(p.channel) && !HIDDEN_CATEGORIES.includes(p.category));

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Notifications</h1>
        {hasUnread && (
          <button onClick={markAllRead} className="text-sm text-brand-green font-medium hover:underline">
            Mark all as read
          </button>
        )}
      </div>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{actionError}</div>
      )}

      {notifications.length === 0 ? (
        <EmptyState className="py-12">No notifications yet.</EmptyState>
      ) : (
        <ul className="bg-white rounded border border-hairline divide-y divide-hairline">
          {notifications.map(n => (
            <li
              key={n.id}
              onClick={() => !n.read && markRead(n.id)}
              className={`px-4 py-3 text-sm flex gap-3 ${n.read ? 'text-gray-500' : 'text-gray-800 cursor-pointer'}`}
            >
              <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${n.read ? 'bg-transparent' : 'bg-brand-green'}`} />
              <span className="flex-1">
                {n.message}
                <span className="block text-xs text-gray-400 mt-0.5">
                  {new Date(n.created_at).toLocaleString('en-ZA', { dateStyle: 'medium', timeStyle: 'short' })}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {next && (
        <button onClick={loadMore} className="text-sm text-brand-green font-medium hover:underline">Load older notifications</button>
      )}

      {visiblePrefs.length > 0 && (
        <section className="bg-white rounded border border-hairline p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Email me about</h2>
          <div className="space-y-3">
            {visiblePrefs.map(p => (
              <label key={p.id} className="flex items-center justify-between gap-4 text-sm">
                <span className="text-gray-700">
                  {CATEGORY_LABELS[p.category] ?? p.category}
                </span>
                <input type="checkbox" checked={p.enabled} onChange={() => togglePref(p)} className="w-4 h-4 accent-brand-green" />
              </label>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
