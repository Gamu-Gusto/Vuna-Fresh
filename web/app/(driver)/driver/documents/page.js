'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { apiClient, openPrivateFile, postForm } from '@/lib/api';
import { Panel } from '@/components/dashboard/widgets';

// Step 2 of 2: the documents an admin checks before approving a driver.
// Stored privately: only this driver and Vuna Fresh admins can open them.
// The list depends on nationality (see backend driver_verification.py).

const STATUS_LABELS = {
  submitted: { text: 'Uploaded, waiting to be checked', tone: 'text-gray-600' },
  accepted: { text: 'Accepted', tone: 'text-brand-green' },
  rejected: { text: 'Needs a new upload', tone: 'text-ember' },
};

function errorText(err) {
  if (!err.detail || typeof err.detail !== 'object') return err.message;
  return Object.values(err.detail).flat().join(' ');
}

export default function DriverDocumentsPage() {
  const [checklist, setChecklist] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/users/me/driver-documents/')
      .then(setChecklist)
      .catch(err => setError(err.message));
  }, []);

  if (error && !checklist) return <p className="py-20 text-center text-sm text-ember">{error}</p>;
  if (!checklist) return <p className="py-20 text-center text-sm text-gray-400">Loading your documents…</p>;

  const done = checklist.items.filter(i => i.document && i.document.status !== 'rejected').length;
  const total = checklist.items.length;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <p className="text-sm text-gray-500">Step 2 of 2</p>
        <h1 className="text-2xl font-bold text-navy mt-1">Your documents</h1>
        <p className="text-sm text-gray-600 mt-1">
          {checklist.is_approved
            ? 'You’re approved. Upload a new version here when a document expires, e.g. your licence disc.'
            : 'Upload every document below. You can do it over several visits; we keep what you’ve already uploaded.'}
        </p>
      </div>

      {checklist.rejection_reason && !checklist.is_approved && (
        <div className="rounded-2xl border border-ember/30 bg-red-50 px-5 py-4 text-sm text-red-800" role="alert">
          Your application was turned down: {checklist.rejection_reason}. Contact support if you think this is a mistake.
        </div>
      )}

      <ConsentPanel checklist={checklist} onChange={setChecklist} />

      {checklist.consent_given && (
        <Panel title={`Checklist (${done} of ${total})`}>
          <div className="h-2 rounded-full bg-brand-bg overflow-hidden mb-4" aria-hidden="true">
            <div className="h-full bg-brand-green rounded-full transition-[width]" style={{ width: `${(done / total) * 100}%` }} />
          </div>
          <ul className="divide-y divide-[#EEF1EC] -my-2">
            {checklist.items.map(item => (
              <DocumentRow key={item.doc_type} item={item} onUploaded={setChecklist} />
            ))}
          </ul>
        </Panel>
      )}

      {checklist.consent_given && !checklist.is_approved && (
        <p className="text-sm text-gray-600">
          {checklist.complete
            ? 'Everything is in. The Vuna Fresh team will check your documents and let you know.'
            : 'Once everything is uploaded, the Vuna Fresh team checks your documents. We’ll notify you if anything needs a new upload.'}
          {' '}<Link href="/driver/dashboard" className="text-brand-green font-medium hover:underline">Back to your dashboard</Link>
        </p>
      )}
    </div>
  );
}

function ConsentPanel({ checklist, onChange }) {
  const [ticked, setTicked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function save(granted) {
    if (!granted && !window.confirm(
      'Withdraw your consent? You can’t be approved without it, and the documents you’ve uploaded will be deleted.',
    )) return;
    setError('');
    setSaving(true);
    try {
      onChange(await apiClient.post('/users/me/driver-documents/consent/', { granted }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (checklist.consent_given) {
    return (
      <p className="text-xs text-gray-500">
        You agreed that Vuna Fresh may collect and check these documents to approve you as a driver.{' '}
        {!checklist.is_approved && (
          <button type="button" onClick={() => save(false)} disabled={saving} className="underline hover:text-ember">
            Withdraw consent
          </button>
        )}
      </p>
    );
  }

  return (
    <Panel title="Before you upload">
      <p className="text-sm text-gray-700">
        To approve you as a driver, Vuna Fresh needs copies of your identity, driving licence, vehicle, address and bank
        documents. They&apos;re stored privately: only you and the Vuna Fresh team can open them, and every time the team
        views one it&apos;s recorded. If your application is turned down or not finished, they&apos;re deleted after 30 days.
      </p>
      <label className="mt-4 flex items-start gap-2 text-sm text-gray-800 cursor-pointer">
        <input type="checkbox" checked={ticked} onChange={e => setTicked(e.target.checked)} className="mt-0.5 w-4 h-4 accent-brand-green" />
        I agree that Vuna Fresh may collect and verify these documents to approve me as a driver.
      </label>
      {error && <p className="mt-2 text-sm text-ember">{error}</p>}
      <button onClick={() => save(true)} disabled={!ticked || saving} className="mt-4 btn-primary text-sm px-4 py-2 disabled:opacity-60">
        {saving ? 'Saving…' : 'Agree and continue'}
      </button>
    </Panel>
  );
}

function DocumentRow({ item, onUploaded }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const doc = item.document;
  const status = doc ? STATUS_LABELS[doc.status] : null;

  async function upload(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      onUploaded(await postForm('/users/me/driver-documents/', { doc_type: item.doc_type, file }));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <li className="py-4 flex flex-wrap items-start gap-x-4 gap-y-2">
      <span
        className={`mt-0.5 w-6 h-6 shrink-0 rounded-full grid place-items-center text-xs font-bold ${
          !doc ? 'border-2 border-gray-300' : doc.status === 'rejected' ? 'bg-ember text-white' : 'bg-brand-green text-white'
        }`}
        aria-hidden="true"
      >
        {doc ? (doc.status === 'rejected' ? '!' : '✓') : ''}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-semibold text-navy">{item.label}</span>
        <span className="block text-sm text-gray-500">{item.hint}</span>
        {doc && (
          <span className={`block text-sm mt-1 ${status.tone}`}>
            {status.text}
            {doc.status === 'rejected' && doc.review_note && `: ${doc.review_note}`}
            {doc.original_name && (
              <>
                {' · '}
                <button
                  type="button"
                  onClick={() => openPrivateFile(`/users/me/driver-documents/${item.doc_type}/file/`).catch(err => setError(err.message))}
                  className="underline text-gray-600 hover:text-navy"
                >
                  {doc.original_name}
                </button>
              </>
            )}
          </span>
        )}
        {error && <span className="block text-sm text-ember mt-1">{error}</span>}
      </span>
      <span>
        <input
          ref={inputRef} type="file" accept="application/pdf,image/jpeg,image/png,image/webp"
          onChange={upload} className="hidden" aria-label={`Upload ${item.label}`}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className={`text-sm font-semibold rounded-full px-4 py-1.5 disabled:opacity-60 ${
            doc && doc.status !== 'rejected'
              ? 'text-brand-green border border-brand-green/30 hover:bg-leaf'
              : 'btn-primary'
          }`}
        >
          {uploading ? 'Uploading…' : doc ? 'Replace' : 'Upload'}
        </button>
      </span>
    </li>
  );
}
