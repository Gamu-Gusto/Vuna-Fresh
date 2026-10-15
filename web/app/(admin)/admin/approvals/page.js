'use client';

import { useState, useEffect } from 'react';
import { apiClient, openPrivateFile } from '@/lib/api';

// Farmer/driver review uses action 'approve'/'reject' at /admin/{type}s/{id}/review/.
// Business buyer review uses action 'approve'/'suspend' at /buyers/admin/business/{id}/review/
// — different verb, different URL shape (apps.buyers, not apps.users), so it
// needs its own small config rather than fitting the farmer/driver pattern.
const BUSINESS_CONFIG = {
  reviewUrl: id => `/buyers/admin/business/${id}/review/`,
  rejectAction: 'suspend',
  rejectLabel: 'Suspend',
};

export default function ApprovalsPage() {
  const [farmers, setFarmers] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Track which profile is being rejected and its typed reason
  const [rejectState, setRejectState] = useState(null); // { id, type, reason }
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [f, d, b] = await Promise.all([
          apiClient.get('/admin/farmers/?pending=true'),
          apiClient.get('/admin/drivers/?pending=true'),
          apiClient.get('/buyers/admin/business/?pending=true'),
        ]);
        setFarmers(f);
        setDrivers(d);
        setBusinesses(b);
      } catch {
        setError('Could not load approval queue.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function reviewUrl(id, type) {
    return type === 'business' ? BUSINESS_CONFIG.reviewUrl(id) : `/admin/${type}s/${id}/review/`;
  }

  function removeFromQueue(id, type) {
    if (type === 'farmer') setFarmers(fs => fs.filter(f => f.id !== id));
    else if (type === 'driver') setDrivers(ds => ds.filter(d => d.id !== id));
    else setBusinesses(bs => bs.filter(b => b.id !== id));
  }

  async function handleApprove(id, type) {
    setActionError('');
    setActionLoading(true);
    try {
      await apiClient.post(reviewUrl(id, type), { action: 'approve' });
      removeFromQueue(id, type);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRejectSubmit() {
    if (!rejectState?.reason?.trim()) return;
    setActionError('');
    setActionLoading(true);
    try {
      const { id, type } = rejectState;
      const action = type === 'business' ? BUSINESS_CONFIG.rejectAction : 'reject';
      await apiClient.post(reviewUrl(id, type), { action, reason: rejectState.reason.trim() });
      removeFromQueue(id, type);
      setRejectState(null);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-400 text-sm">Loading…</div>;
  if (error) return <div className="text-center py-20 text-red-500 text-sm">{error}</div>;

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-bold text-gray-900">Approval queue</h1>

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {actionError}
        </div>
      )}

      <Section title="Pending farmers" count={farmers.length}>
        {farmers.length === 0 ? (
          <AllClear>No farmers waiting for approval.</AllClear>
        ) : (
          <div className="space-y-3">
            {farmers.map(f => (
              <ApprovalCard
                key={f.id}
                name={f.full_name}
                email={f.email}
                dateJoined={f.date_joined}
                detail={[
                  f.farm_name && `Farm: ${f.farm_name}`,
                  f.farm_location && `Location: ${f.farm_location}`,
                ].filter(Boolean)}
                rejecting={rejectState?.id === f.id && rejectState?.type === 'farmer'}
                rejectReason={rejectState?.id === f.id ? rejectState.reason : ''}
                onApprove={() => handleApprove(f.id, 'farmer')}
                onRejectClick={() => setRejectState({ id: f.id, type: 'farmer', reason: '' })}
                onRejectReasonChange={reason => setRejectState(s => ({ ...s, reason }))}
                onRejectSubmit={handleRejectSubmit}
                onRejectCancel={() => setRejectState(null)}
                loading={actionLoading}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="Pending drivers" count={drivers.length}>
        {drivers.length === 0 ? (
          <AllClear>No drivers waiting for approval.</AllClear>
        ) : (
          <div className="space-y-3">
            {drivers.map(d => (
              <ApprovalCard
                key={d.id}
                name={d.full_name}
                email={d.email}
                dateJoined={d.date_joined}
                detail={[
                  d.age != null && `Age ${d.age}`,
                  d.nationality === 'sa_citizen' && `SA citizen, ID ${d.id_number}`,
                  d.nationality === 'foreign_national' && `Foreign national, passport ${d.passport_number}`,
                  d.vehicle_type && `Vehicle: ${d.vehicle_type}`,
                  d.vehicle_registration && `Reg: ${d.vehicle_registration}`,
                ].filter(Boolean)}
                approveBlockedReason={driverBlockedReason(d)}
                extra={
                  <DriverDocuments
                    driver={d}
                    onChange={updated => setDrivers(ds => ds.map(x => (x.id === updated.id ? updated : x)))}
                    onError={setActionError}
                  />
                }
                rejecting={rejectState?.id === d.id && rejectState?.type === 'driver'}
                rejectReason={rejectState?.id === d.id ? rejectState.reason : ''}
                onApprove={() => handleApprove(d.id, 'driver')}
                onRejectClick={() => setRejectState({ id: d.id, type: 'driver', reason: '' })}
                onRejectReasonChange={reason => setRejectState(s => ({ ...s, reason }))}
                onRejectSubmit={handleRejectSubmit}
                onRejectCancel={() => setRejectState(null)}
                loading={actionLoading}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="Pending businesses" count={businesses.length}>
        {businesses.length === 0 ? (
          <AllClear>No businesses waiting for approval.</AllClear>
        ) : (
          <div className="space-y-3">
            {businesses.map(b => (
              <ApprovalCard
                key={b.id}
                name={b.full_name}
                email={b.email}
                dateJoined={b.created_at}
                detail={[
                  b.business_name && `Business: ${b.business_name}`,
                  b.business_type && `Type: ${b.business_type}`,
                  b.credit_terms && `Terms: ${b.credit_terms}`,
                ].filter(Boolean)}
                rejectLabel={BUSINESS_CONFIG.rejectLabel}
                rejecting={rejectState?.id === b.id && rejectState?.type === 'business'}
                rejectReason={rejectState?.id === b.id ? rejectState.reason : ''}
                onApprove={() => handleApprove(b.id, 'business')}
                onRejectClick={() => setRejectState({ id: b.id, type: 'business', reason: '' })}
                onRejectReasonChange={reason => setRejectState(s => ({ ...s, reason }))}
                onRejectSubmit={handleRejectSubmit}
                onRejectCancel={() => setRejectState(null)}
                loading={actionLoading}
              />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, count, children }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-2">
        {title}
        {count > 0 && (
          <span className="ml-2 font-normal text-amber-800">({count} waiting)</span>
        )}
      </h2>
      {children}
    </div>
  );
}

function AllClear({ children }) {
  return (
    <div className="text-gray-600">
      {children}
    </div>
  );
}

// Why a driver can't be approved yet (mirrors the backend rule), or null
function driverBlockedReason(d) {
  const v = d.verification;
  if (!v || v.complete) return null;
  if (!v.old_enough) return 'Not 21 or older, or no date of birth.';
  if (!v.consent_given) return 'Hasn’t agreed to the document check yet.';
  if (v.missing.length) return `Still to upload: ${v.missing.join(', ')}.`;
  if (v.rejected.length) return `Waiting for a new upload: ${v.rejected.join(', ')}.`;
  return 'Application not complete.';
}

const DOC_STATUS = {
  submitted: { text: 'To check', tone: 'text-amber-700' },
  accepted: { text: 'Accepted', tone: 'text-brand-green' },
  rejected: { text: 'Rejected', tone: 'text-ember' },
};

// The driver's documents: view (logged), accept, or reject with a note the driver sees
function DriverDocuments({ driver, onChange, onError }) {
  const [rejecting, setRejecting] = useState(null); // { id, note }
  const [busy, setBusy] = useState(null);

  async function review(docId, body) {
    onError('');
    setBusy(docId);
    try {
      onChange(await apiClient.post(`/admin/drivers/${driver.id}/documents/${docId}/review/`, body));
      setRejecting(null);
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(null);
    }
  }

  if (!driver.documents?.length) {
    return <p className="mt-3 text-sm text-gray-500">No documents uploaded yet.</p>;
  }
  return (
    <ul className="mt-4 border-t border-hairline divide-y divide-hairline">
      {driver.documents.map(doc => (
        <li key={doc.id} className="py-2 text-sm">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="min-w-0 flex-1 text-gray-800">{doc.label}</span>
            <span className={DOC_STATUS[doc.status].tone}>{DOC_STATUS[doc.status].text}</span>
            <button
              type="button"
              onClick={() => openPrivateFile(`/admin/drivers/${driver.id}/documents/${doc.id}/file/`).catch(err => onError(err.message))}
              className="text-brand-green font-medium hover:underline"
            >
              View
            </button>
            {doc.status !== 'accepted' && (
              <button type="button" disabled={busy === doc.id} onClick={() => review(doc.id, { action: 'accept' })} className="text-gray-700 hover:text-brand-green disabled:opacity-60">
                Accept
              </button>
            )}
            {doc.status !== 'rejected' && (
              <button type="button" disabled={busy === doc.id} onClick={() => setRejecting({ id: doc.id, note: '' })} className="text-gray-700 hover:text-ember disabled:opacity-60">
                Reject
              </button>
            )}
          </div>
          {doc.status === 'rejected' && doc.review_note && <p className="text-xs text-gray-500 mt-0.5">Note to driver: {doc.review_note}</p>}
          {rejecting?.id === doc.id && (
            <div className="mt-2 flex flex-wrap gap-2">
              <input
                value={rejecting.note}
                onChange={e => setRejecting(r => ({ ...r, note: e.target.value }))}
                placeholder="What's wrong? The driver sees this, e.g. Older than 3 months"
                aria-label={`Why ${doc.label} is rejected`}
                className="min-w-0 flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
              />
              <button
                type="button"
                disabled={!rejecting.note.trim() || busy === doc.id}
                onClick={() => review(doc.id, { action: 'reject', note: rejecting.note.trim() })}
                className="bg-red-600 text-white text-sm font-semibold px-3 py-1.5 rounded-lg disabled:opacity-60"
              >
                Reject document
              </button>
              <button type="button" onClick={() => setRejecting(null)} className="text-sm text-gray-500 px-2">Cancel</button>
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

function ApprovalCard({
  name, email, dateJoined, detail, extra = null, approveBlockedReason = null,
  rejecting, rejectReason, rejectLabel = 'Reject',
  onApprove, onRejectClick, onRejectReasonChange, onRejectSubmit, onRejectCancel,
  loading,
}) {
  return (
    <div className="bg-white rounded border border-hairline p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900">{name}</p>
          <p className="text-sm text-gray-500">{email}</p>
          {detail.length > 0 && (
            <p className="text-sm text-gray-600 mt-1">{detail.join(', ')}</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            Applied {new Date(dateJoined).toLocaleDateString('en-ZA')}
          </p>
          {approveBlockedReason && <p className="text-sm text-amber-700 mt-1">{approveBlockedReason}</p>}
        </div>

        {!rejecting && (
          <div className="flex gap-2 shrink-0">
            <button
              onClick={onApprove}
              disabled={loading || Boolean(approveBlockedReason)}
              title={approveBlockedReason ?? undefined}
              className="btn-primary text-sm px-4 py-1.5 disabled:opacity-60"
            >
              Approve
            </button>
            <button
              onClick={onRejectClick}
              disabled={loading}
              className="bg-white text-red-600 border border-red-200 text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-60"
            >
              {rejectLabel}
            </button>
          </div>
        )}
      </div>

      {extra}

      {rejecting && (
        <div className="mt-4 border-t border-hairline pt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {rejectLabel} reason <span className="text-red-500">*</span>
          </label>
          <textarea
            value={rejectReason}
            onChange={e => onRejectReasonChange(e.target.value)}
            rows={2}
            placeholder={`Explain why this application is being ${rejectLabel.toLowerCase()}ed…`}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={onRejectSubmit}
              disabled={loading || !rejectReason?.trim()}
              className="bg-red-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-60"
            >
              {loading ? `${rejectLabel}ing…` : `Confirm ${rejectLabel.toLowerCase()}`}
            </button>
            <button
              onClick={onRejectCancel}
              disabled={loading}
              className="text-sm text-gray-500 hover:text-gray-700 px-4 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
