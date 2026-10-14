'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import Spinner from './Spinner';
import ErrorMessage from './ErrorMessage';
import EmptyState from './EmptyState';
import StatusText from './StatusText';

export const ISSUE_CATEGORIES = [
  { value: 'missing_item', label: 'Missing item' },
  { value: 'damaged_item', label: 'Damaged item' },
  { value: 'wrong_order', label: 'Wrong order' },
  { value: 'late_delivery', label: 'Late delivery' },
  { value: 'payment_issue', label: 'Payment issue' },
  { value: 'account_issue', label: 'Account issue' },
  { value: 'app_bug', label: 'Something isn’t working' },
];
const CATEGORY_LABEL = Object.fromEntries(ISSUE_CATEGORIES.map(c => [c.value, c.label]));

const STATUS_STYLE = {
  open: { tone: 'action', label: 'Open' },
  in_progress: { tone: 'normal', label: 'Being looked at' },
  resolved: { tone: 'done', label: 'Resolved' },
  closed: { tone: 'quiet', label: 'Closed' },
};

const RESOLUTIONS = [
  { value: 'none', label: 'None' },
  { value: 'refund', label: 'Refund' },
  { value: 'replacement', label: 'Replacement' },
  { value: 'discount', label: 'Discount' },
];

const inputClass =
  'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent';

export function IssueStatusBadge({ status }) {
  const style = STATUS_STYLE[status] ?? { tone: 'normal', label: status };
  return <StatusText label={style.label} tone={style.tone} />;
}

/** List of the user's issues plus a "report a problem" form. basePath links to the thread page. */
export function SupportList({ basePath, admin = false }) {
  const [issues, setIssues] = useState([]);
  const [orders, setOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState(admin ? 'open' : '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    apiClient.get(`/issues/${statusFilter ? `?status=${statusFilter}` : ''}`)
      .then(data => setIssues(data.results ?? data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => {
    if (admin) return;
    apiClient.get('/orders/').then(data => setOrders(data.results ?? data)).catch(() => {});
  }, [admin]);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{admin ? 'Support issues' : 'Help & support'}</h1>
          {!admin && <p className="text-sm text-gray-500 mt-1">Problem with an order or the app? Let us know and we’ll sort it out.</p>}
        </div>
        {admin ? (
          <select value={statusFilter} onChange={e => { setLoading(true); setStatusFilter(e.target.value); }} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white">
            <option value="">All</option>
            {Object.entries(STATUS_STYLE).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
          </select>
        ) : (
          !showForm && <button onClick={() => setShowForm(true)} className="btn-primary text-sm px-4 py-2">Report a problem</button>
        )}
      </div>

      {showForm && (
        <NewIssueForm
          orders={orders}
          onCancel={() => setShowForm(false)}
          onCreated={issue => {
            setIssues(is => [issue, ...is]);
            setShowForm(false);
          }}
        />
      )}

      {loading ? <Spinner /> : error ? <ErrorMessage message={error} /> : issues.length === 0 ? (
        <EmptyState className="py-12">{admin ? 'No issues here.' : 'You haven’t reported any problems.'}</EmptyState>
      ) : (
        <ul className="bg-white rounded border border-hairline divide-y divide-hairline">
          {issues.map(issue => (
            <li key={issue.id}>
              <Link href={`${basePath}/${issue.id}`} className="flex items-start justify-between gap-4 px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0 text-sm">
                  <p className="font-medium text-gray-800">
                    <span className="font-mono text-gray-400">#{issue.id}</span> {CATEGORY_LABEL[issue.category] ?? issue.category}
                    {issue.order && <span className="text-gray-500 font-normal"> on order <span className="font-mono">#{issue.order}</span></span>}
                  </p>
                  <p className="text-gray-500 truncate">{issue.description}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {admin && <>{issue.reporter_email}, </>}
                    {new Date(issue.created_at).toLocaleDateString('en-ZA')}
                  </p>
                </div>
                <IssueStatusBadge status={issue.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NewIssueForm({ orders, onCreated, onCancel }) {
  const [form, setForm] = useState({ category: 'missing_item', order: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function update(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const issue = await apiClient.post('/issues/', {
        category: form.category,
        order: form.order ? Number(form.order) : null,
        description: form.description.trim(),
      });
      onCreated(issue);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-5 space-y-4">
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">What’s wrong?</label>
          <select name="category" value={form.category} onChange={update} className={`${inputClass} bg-white`}>
            {ISSUE_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Order (optional)</label>
          <select name="order" value={form.order} onChange={update} className={`${inputClass} bg-white`}>
            <option value="">Not about an order</option>
            {orders.map(o => (
              <option key={o.id} value={o.id}>
                #{o.id}, {new Date(o.created_at).toLocaleDateString('en-ZA')}, R{Number(o.total).toFixed(2)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Tell us what happened</label>
        <textarea name="description" value={form.description} onChange={update} rows={4} required className={inputClass} />
      </div>
      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>}
      <div className="flex gap-2">
        <button type="submit" disabled={saving || !form.description.trim()} className="btn-primary text-sm px-4 py-2 disabled:opacity-60">
          {saving ? 'Sending…' : 'Send'}
        </button>
        <button type="button" onClick={onCancel} className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2">Cancel</button>
      </div>
    </form>
  );
}

/** One issue's conversation. Admins also get status/resolution controls. */
export function SupportThread({ id, backHref, admin = false }) {
  const [issue, setIssue] = useState(null);
  const [error, setError] = useState('');
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    apiClient.get(`/issues/${id}/`).then(setIssue).catch(err => setError(err.message));
  }, [id]);

  async function sendReply(e) {
    e.preventDefault();
    setActionError('');
    setSending(true);
    try {
      const message = await apiClient.post(`/issues/${id}/messages/`, { message: reply.trim() });
      setIssue(i => ({ ...i, messages: [...i.messages, message] }));
      setReply('');
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function updateStatus(changes) {
    setActionError('');
    try {
      setIssue(await apiClient.patch(`/issues/${id}/set_status/`, changes));
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function rate(rating, comment) {
    setActionError('');
    try {
      const saved = await apiClient.post(`/issues/${id}/rate/`, { rating, comment });
      setIssue(i => ({ ...i, rating: saved }));
    } catch (err) {
      setActionError(err.message);
    }
  }

  if (error) return <ErrorMessage message={error} />;
  if (!issue) return <Spinner />;

  const finished = issue.status === 'resolved' || issue.status === 'closed';

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Link href={backHref} className="text-gray-400 hover:text-gray-600">← Support</Link>
        <span className="text-gray-300">/</span>
        <span className="font-semibold text-gray-800">Issue <span className="font-mono">#{issue.id}</span></span>
        <IssueStatusBadge status={issue.status} />
      </div>

      <div className="bg-white rounded border border-hairline p-5 text-sm space-y-2">
        <p className="font-semibold text-gray-800">
          {CATEGORY_LABEL[issue.category] ?? issue.category}
          {issue.order && (
            <span className="font-normal text-gray-500">
              {' on '}
              {admin
                ? <Link href={`/admin/orders/${issue.order}`} className="hover:underline">order <span className="font-mono">#{issue.order}</span></Link>
                : <>order <span className="font-mono">#{issue.order}</span></>}
            </span>
          )}
        </p>
        <p className="text-gray-700 whitespace-pre-line">{issue.description}</p>
        <p className="text-xs text-gray-400">
          {admin && <>{issue.reporter_email}. </>}Reported {new Date(issue.created_at).toLocaleString('en-ZA')}
          {issue.resolution_type !== 'none' && <>. Resolution: <span className="capitalize">{issue.resolution_type}</span></>}
        </p>
      </div>

      {admin && (
        <div className="bg-white rounded border border-hairline p-4 flex flex-wrap items-end gap-4 text-sm">
          <label>
            <span className="block text-gray-500 mb-1">Status</span>
            <select value={issue.status} onChange={e => updateStatus({ status: e.target.value })} className="border border-gray-300 rounded-lg px-3 py-1.5 bg-white">
              {Object.entries(STATUS_STYLE).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
            </select>
          </label>
          <label>
            <span className="block text-gray-500 mb-1">Resolution</span>
            <select value={issue.resolution_type} onChange={e => updateStatus({ resolution_type: e.target.value })} className="border border-gray-300 rounded-lg px-3 py-1.5 bg-white">
              {RESOLUTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </label>
        </div>
      )}

      {actionError && <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{actionError}</div>}

      <div className="space-y-3">
        {issue.messages.map(m => {
          const fromSupport = m.sender_role === 'admin';
          return (
            <div key={m.id} className={`flex ${fromSupport === admin ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded px-4 py-2.5 text-sm ${fromSupport ? 'bg-navy text-gray-100' : 'bg-white border border-hairline text-gray-800'}`}>
                <p className={`text-xs mb-1 ${fromSupport ? 'text-gray-400' : 'text-gray-400'}`}>
                  {fromSupport ? 'Vuna Fresh support' : admin ? m.sender_email : 'You'}, {new Date(m.sent_at).toLocaleString('en-ZA', { dateStyle: 'short', timeStyle: 'short' })}
                </p>
                <p className="whitespace-pre-line">{m.message}</p>
              </div>
            </div>
          );
        })}
      </div>

      {issue.status !== 'closed' && (
        <form onSubmit={sendReply} className="bg-white rounded border border-hairline p-4 space-y-3">
          <textarea value={reply} onChange={e => setReply(e.target.value)} rows={3} placeholder="Write a reply…" className={inputClass} />
          <button type="submit" disabled={sending || !reply.trim()} className="btn-primary text-sm px-4 py-2 disabled:opacity-60">
            {sending ? 'Sending…' : 'Send reply'}
          </button>
        </form>
      )}

      {!admin && finished && !issue.rating && <RateSupport onRate={rate} />}
      {issue.rating && (
        <p className="text-sm text-gray-500">
          Rated <span className="text-amber-500">{'★'.repeat(issue.rating.rating)}</span>
          {issue.rating.comment && <>: “{issue.rating.comment}”</>}
        </p>
      )}
    </div>
  );
}

function RateSupport({ onRate }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');

  return (
    <div className="bg-white rounded border border-hairline p-4 space-y-3 text-sm">
      <p className="font-medium text-gray-800">How did we do?</p>
      <StarPicker value={rating} onChange={setRating} />
      <textarea value={comment} onChange={e => setComment(e.target.value)} rows={2} placeholder="Anything to add? (optional)" className={inputClass} />
      <button onClick={() => onRate(rating, comment.trim())} disabled={!rating} className="btn-primary text-sm px-4 py-2 disabled:opacity-60">
        Submit rating
      </button>
    </div>
  );
}

export function StarPicker({ value, onChange }) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n > 1 ? 's' : ''}`}
          onClick={() => onChange(n)}
          className={`text-2xl leading-none ${n <= value ? 'text-amber-500' : 'text-gray-300'} hover:text-amber-400`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
