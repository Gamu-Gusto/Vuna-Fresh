'use client';

import { useState } from 'react';

// The Vuna Fresh bank account plus what to pay, with copy buttons for the
// fields people type into their banking app.
export default function BankDetails({ details, amount, reference }) {
  return (
    <dl className="text-sm divide-y divide-hairline">
      <BankRow label="Bank" value={details.bank_name} />
      <BankRow label="Account holder" value={details.account_holder} />
      <BankRow label="Account number" value={details.account_number} copy mono />
      <BankRow label="Branch code" value={details.branch_code} copy mono />
      {details.account_type && <BankRow label="Account type" value={details.account_type} />}
      {amount != null && <BankRow label="Amount" value={`R${Number(amount).toFixed(2)}`} mono />}
      {reference && <BankRow label="Reference" value={reference} copy mono highlight />}
    </dl>
  );
}

function BankRow({ label, value, copy, mono, highlight }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  }

  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <dt className="text-gray-500">{label}</dt>
      <dd className={`flex items-center gap-2 text-right ${mono ? 'font-mono' : ''} ${highlight ? 'font-semibold text-gray-900' : 'text-gray-800'}`}>
        {value || '—'}
        {copy && value && (
          <button type="button" onClick={handleCopy} className="text-xs font-sans text-brand-green hover:underline">
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </dd>
    </div>
  );
}
