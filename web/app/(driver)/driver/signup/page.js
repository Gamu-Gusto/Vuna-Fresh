'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ConsentCheckboxes, { INITIAL_CONSENT } from '@/components/ConsentCheckboxes';

// Step 1 of 2: the account, identity and vehicle. Drivers must be 21 or older.
// Step 2 is the document checklist at /driver/documents, which they can finish
// over several visits. The backend repeats every check here.
const MINIMUM_AGE = 21;

function ageOn(dateOfBirth) {
  const dob = new Date(`${dateOfBirth}T00:00:00`);
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  if (today.getMonth() < dob.getMonth() || (today.getMonth() === dob.getMonth() && today.getDate() < dob.getDate())) age -= 1;
  return age;
}

function errorText(err) {
  if (!err.detail || typeof err.detail !== 'object') return err.message;
  return Object.values(err.detail).flat().join(' ');
}

export default function DriverSignupPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    date_of_birth: '', nationality: '', id_number: '', passport_number: '',
    vehicle_type: '', vehicle_registration: '',
    password: '', password_confirm: '',
  });
  const [consent, setConsent] = useState(INITIAL_CONSENT);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  const tooYoung = form.date_of_birth && ageOn(form.date_of_birth) < MINIMUM_AGE;
  const latestBirthday = (() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - MINIMUM_AGE);
    return d.toLocaleDateString('en-CA');
  })();

  async function handleSubmit(e) {
    e.preventDefault();
    if (tooYoung) return;
    setError('');
    setLoading(true);
    try {
      const saCitizen = form.nationality === 'sa_citizen';
      await register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        phone: form.phone,
        password: form.password,
        password_confirm: form.password_confirm,
        role: 'driver',
        date_of_birth: form.date_of_birth,
        nationality: form.nationality,
        id_number: saCitizen ? form.id_number.replace(/\s/g, '') : '',
        passport_number: saCitizen ? '' : form.passport_number.trim(),
        vehicle_type: form.vehicle_type,
        vehicle_registration: form.vehicle_registration,
        ...consent,
      });
      // Signed in: on to step 2, the document checklist
      router.push('/driver/documents');
    } catch (err) {
      setError(errorText(err));
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto mt-12 px-4 pb-16">
      <div className="mb-6">
        <p className="text-sm text-gray-500">Step 1 of 2</p>
        <h1 className="type-display text-5xl mt-1">Drive with Vuna Fresh</h1>
        <p className="text-gray-600 mt-2">
          {`You need to be ${MINIMUM_AGE} or older. `}
          After this you&apos;ll upload your licence, ID, vehicle and bank documents, and the team checks everything
          before you can take deliveries.
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name" name="first_name" value={form.first_name} onChange={handleChange} required autoComplete="given-name" />
          <Field label="Last name" name="last_name" value={form.last_name} onChange={handleChange} required autoComplete="family-name" />
        </div>
        <Field label="Email" name="email" type="email" value={form.email} onChange={handleChange} required autoComplete="email" />
        <Field label="Phone" name="phone" type="tel" value={form.phone} onChange={handleChange} required autoComplete="tel" />

        <div className="border-t border-hairline pt-4 space-y-4">
          <h2 className="text-base font-semibold text-navy">About you</h2>
          <div>
            <Field
              label="Date of birth" name="date_of_birth" type="date" value={form.date_of_birth}
              onChange={handleChange} required max={latestBirthday} autoComplete="bday"
            />
            {tooYoung && (
              <p className="mt-1 text-sm text-ember">Drivers must be {MINIMUM_AGE} or older.</p>
            )}
          </div>

          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 mb-2">Nationality</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['sa_citizen', 'South African citizen'],
                ['foreign_national', 'Foreign national'],
              ].map(([value, label]) => (
                <label
                  key={value}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm cursor-pointer ${form.nationality === value ? 'border-brand-green bg-leaf' : 'border-gray-300'}`}
                >
                  <input
                    type="radio" name="nationality" value={value} checked={form.nationality === value}
                    onChange={handleChange} required className="accent-brand-green"
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>

          {form.nationality === 'sa_citizen' && (
            <div>
              <Field
                label="South African ID number" name="id_number" value={form.id_number} onChange={handleChange}
                required inputMode="numeric" placeholder="13 digits" maxLength={16}
              />
              <p className="mt-1 text-xs text-gray-500">It must match your date of birth. You&apos;ll upload your ID and SA driver&apos;s licence next.</p>
            </div>
          )}
          {form.nationality === 'foreign_national' && (
            <div>
              <Field
                label="Passport number" name="passport_number" value={form.passport_number} onChange={handleChange}
                required maxLength={20}
              />
              <p className="mt-1 text-xs text-gray-500">
                You&apos;ll upload your passport, your national or international driving licence, and your work permit or asylum
                document next.
              </p>
            </div>
          )}
        </div>

        <div className="border-t border-hairline pt-4">
          <h2 className="text-base font-semibold text-navy mb-3">Vehicle details</h2>
          <div className="space-y-4">
            <Field
              label="Vehicle type" name="vehicle_type" value={form.vehicle_type} onChange={handleChange}
              placeholder="e.g. Sedan, Bakkie, Motorbike" required
            />
            <Field
              label="Registration number" name="vehicle_registration" value={form.vehicle_registration}
              onChange={handleChange} placeholder="e.g. CA 123-456" required
            />
          </div>
        </div>

        <div className="border-t border-hairline pt-4">
          <h2 className="text-base font-semibold text-navy mb-3">Password</h2>
          <div className="space-y-4">
            <Field label="Password" name="password" type="password" value={form.password} onChange={handleChange} required autoComplete="new-password" />
            <Field label="Confirm password" name="password_confirm" type="password" value={form.password_confirm} onChange={handleChange} required autoComplete="new-password" />
          </div>
        </div>

        <ConsentCheckboxes value={consent} onChange={setConsent} />

        <button type="submit" disabled={loading || tooYoung} className="w-full btn-primary py-2.5">
          {loading ? 'Creating your account…' : 'Continue to documents'}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-gray-500">
        Already have an account?{' '}
        <Link href="/driver/login" className="text-brand-green font-medium hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}

function Field({ label, name, type = 'text', value, onChange, required, placeholder, ...rest }) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        {...rest}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
    </div>
  );
}
