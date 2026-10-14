import Link from 'next/link';

// POPIA consent captured at signup. The backend refuses signup unless
// accept_privacy_policy is true and records both as ConsentRecords.
export default function ConsentCheckboxes({ value, onChange }) {
  function toggle(e) {
    const { name, checked } = e.target;
    onChange({ ...value, [name]: checked });
  }

  return (
    <div className="space-y-3 text-sm text-gray-700">
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          name="accept_privacy_policy"
          checked={value.accept_privacy_policy}
          onChange={toggle}
          required
          className="mt-0.5"
        />
        <span>
          I agree that Vuna Fresh may process my personal information as described in the{' '}
          <Link href="/privacy" target="_blank" className="text-brand-green font-medium hover:underline">privacy policy</Link>.
          <span className="text-red-500"> *</span>
        </span>
      </label>
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          name="marketing_opt_in"
          checked={value.marketing_opt_in}
          onChange={toggle}
          className="mt-0.5"
        />
        <span>Send me specials and news about seasonal produce. Optional, and you can change it any time.</span>
      </label>
    </div>
  );
}

export const INITIAL_CONSENT = { accept_privacy_policy: false, marketing_opt_in: false };
