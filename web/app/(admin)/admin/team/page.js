'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Panel } from '@/components/dashboard/widgets';

// The admin team, for the super admin only. Managers can do everything an
// admin can except manage this team and pay farmers.

function errorText(err) {
  if (!err.detail || typeof err.detail !== 'object') return err.message;
  return Object.values(err.detail).flat().join(' ');
}

export default function TeamPage() {
  const { user } = useAuth();
  const [staff, setStaff] = useState(null);
  const [error, setError] = useState('');
  const [link, setLink] = useState(null); // { name, url } after an invite or a new link

  const isSuperAdmin = Boolean(user?.is_super_admin);

  useEffect(() => {
    if (!isSuperAdmin) return;
    apiClient.get('/admin/staff/')
      .then(data => setStaff(data.results ?? data))
      .catch(() => setError('Could not load the team.'));
  }, [isSuperAdmin]);

  if (!isSuperAdmin) {
    return (
      <div className="max-w-xl py-10">
        <h1 className="text-2xl font-bold text-navy">Team</h1>
        <p className="mt-2 text-sm text-gray-600">Only the super admin can add or remove admins and managers.</p>
      </div>
    );
  }

  function replace(updated) {
    setStaff(list => list.map(s => (s.id === updated.id ? updated : s)));
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-navy">Team</h1>
        <p className="text-sm text-gray-500 mt-1">
          Managers can do everything you can, except add or remove team members and pay farmers.
        </p>
      </div>

      {link && <LinkNotice link={link} onClose={() => setLink(null)} />}

      <AddManager
        onAdded={(member, url) => {
          setStaff(list => [...(list ?? []), member]);
          setLink({ name: member.first_name, url });
        }}
      />

      <Panel title="Admins and managers">
        {error && <p className="text-sm text-ember">{error}</p>}
        {!staff ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : (
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {staff.map(member => (
              <StaffRow key={member.id} member={member} onChange={replace} onLink={url => setLink({ name: member.first_name, url })} />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function AddManager({ onAdded }) {
  const empty = { first_name: '', last_name: '', email: '', phone: '' };
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const res = await apiClient.post('/admin/staff/', form);
      onAdded(res.staff, res.set_password_link);
      setForm(empty);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  const input = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent';
  const field = (name, label, props = {}) => (
    <div>
      <label htmlFor={`manager-${name}`} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        id={`manager-${name}`} value={form[name]} className={input}
        onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))} {...props}
      />
    </div>
  );

  return (
    <Panel title="Add a manager">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {field('first_name', 'First name', { required: true, autoComplete: 'off' })}
          {field('last_name', 'Last name', { required: true, autoComplete: 'off' })}
          {field('email', 'Email', { type: 'email', required: true, autoComplete: 'off' })}
          {field('phone', 'Phone (optional)', { type: 'tel', autoComplete: 'off' })}
        </div>
        <p className="text-xs text-gray-500">
          They get an email with a link to choose their own password. You&apos;ll also see the link here, to send another way.
        </p>
        {error && <p className="text-sm text-ember">{error}</p>}
        <button type="submit" disabled={saving} className="btn-primary text-sm px-4 py-2">
          {saving ? 'Adding…' : 'Add manager'}
        </button>
      </form>
    </Panel>
  );
}

function StaffRow({ member, onChange, onLink }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = member.status !== 'deactivated';

  async function act(path, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setError('');
    setBusy(true);
    try {
      const res = await apiClient.post(`/admin/staff/${member.id}/${path}/`);
      if (res.set_password_link) onLink(res.set_password_link);
      else onChange(res);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="py-3 flex flex-wrap items-center gap-x-4 gap-y-2">
      <span className="w-10 h-10 shrink-0 rounded-full bg-leaf text-brand-green grid place-items-center text-sm font-semibold" aria-hidden="true">
        {(member.first_name?.[0] ?? member.email[0]).toUpperCase()}
      </span>
      <span className={`min-w-0 flex-1 ${active ? '' : 'opacity-60'}`}>
        <span className="block font-semibold text-navy truncate">{member.full_name || member.email}</span>
        <span className="block text-xs text-gray-500 truncate">
          {member.is_super_admin ? 'Super admin' : 'Manager'}, {member.email}
          {!active && ', deactivated'}
          {active && !member.is_super_admin && !member.last_login && ', hasn’t logged in yet'}
        </span>
      </span>
      {!member.is_super_admin && (
        <span className="flex gap-2">
          {active ? (
            <>
              <button onClick={() => act('set_password_link')} disabled={busy} className="text-xs font-semibold text-brand-green border border-brand-green/30 rounded-full px-3 py-1.5 hover:bg-leaf disabled:opacity-60">
                New password link
              </button>
              <button
                onClick={() => act('deactivate', `Deactivate ${member.full_name || member.email}? They will be logged out and can't log in until you reactivate them.`)}
                disabled={busy}
                className="text-xs font-semibold text-ember border border-ember/30 rounded-full px-3 py-1.5 hover:bg-red-50 disabled:opacity-60"
              >
                Deactivate
              </button>
            </>
          ) : (
            <button onClick={() => act('reactivate')} disabled={busy} className="text-xs font-semibold text-brand-green border border-brand-green/30 rounded-full px-3 py-1.5 hover:bg-leaf disabled:opacity-60">
              Reactivate
            </button>
          )}
        </span>
      )}
      {error && <p className="basis-full text-sm text-ember">{error}</p>}
    </li>
  );
}

// The set-password link, shown once so the super admin can send it another way
// (e.g. WhatsApp) if the email doesn't arrive.
function LinkNotice({ link, onClose }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link.url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="rounded-3xl border border-brand-green/30 bg-leaf p-5 sm:p-6" role="status">
      <h2 className="font-semibold text-navy">Send {link.name} their set-password link</h2>
      <p className="mt-1 text-sm text-gray-700">
        We&apos;ve emailed it too. It works once and expires in 3 days. Anyone with the link can set the password, so send it only to {link.name}.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <input readOnly value={link.url} aria-label="Set-password link" onFocus={e => e.target.select()} className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs text-gray-700" />
        <button onClick={copy} className="btn-primary text-sm px-4 py-2">{copied ? 'Copied' : 'Copy link'}</button>
        <button onClick={onClose} className="text-sm text-gray-600 hover:text-navy px-3">Done</button>
      </div>
    </section>
  );
}
