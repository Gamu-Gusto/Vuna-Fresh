'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ConsentCheckboxes, { INITIAL_CONSENT } from '@/components/ConsentCheckboxes';

export default function DriverSignupPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    vehicle_type: '', vehicle_registration: '',
    password: '', password_confirm: '',
  });
  const [consent, setConsent] = useState(INITIAL_CONSENT);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(false);

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Register the user account (role: driver).
      // Vehicle info can't be saved to the backend at this stage because
      // DriverProfile is created by admin during approval. It's shown on
      // the pending screen so the driver can provide it to admin.
      await register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        phone: form.phone,
        password: form.password,
        password_confirm: form.password_confirm,
        role: 'driver',
        ...consent,
      });
      setPending(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (pending) {
    return (
      <div className="max-w-xl mx-auto mt-12 px-4 pb-16">
        <h1 className="type-display text-5xl">Thanks, we&apos;ve got your application</h1>
        <p className="mt-4 text-gray-700 leading-relaxed">
          The Vuna Fresh team will check your details and get in touch. Once you&apos;re approved you can{' '}
          <Link href="/driver/login" className="text-brand-green font-semibold underline underline-offset-4">log in</Link>{' '}
          and see your deliveries.
        </p>
        <dl className="mt-6 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-sm">
          <dt className="text-gray-500">Vehicle</dt><dd className="text-gray-900">{form.vehicle_type || 'Not given'}</dd>
          <dt className="text-gray-500">Registration</dt><dd className="text-gray-900">{form.vehicle_registration || 'Not given'}</dd>
          <dt className="text-gray-500">Email</dt><dd className="text-gray-900">{form.email}</dd>
        </dl>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto mt-12 px-4 pb-16">
      <div className="mb-6">
        <h1 className="type-display text-5xl">Drive with Vuna Fresh</h1>
        <p className="text-gray-600 mt-2">
          Your account will be reviewed before you can be assigned deliveries.
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name" name="first_name" value={form.first_name} onChange={handleChange} required />
          <Field label="Last name" name="last_name" value={form.last_name} onChange={handleChange} required />
        </div>
        <Field label="Email" name="email" type="email" value={form.email} onChange={handleChange} required />
        <Field label="Phone" name="phone" type="tel" value={form.phone} onChange={handleChange} required />

        <div className="border-t border-hairline pt-4">
          <h2 className="text-base font-semibold text-navy mb-3">Vehicle details</h2>
          <div className="space-y-4">
            <Field
              label="Vehicle type"
              name="vehicle_type"
              value={form.vehicle_type}
              onChange={handleChange}
              placeholder="e.g. Sedan, Bakkie, Motorbike"
              required
            />
            <Field
              label="Registration number"
              name="vehicle_registration"
              value={form.vehicle_registration}
              onChange={handleChange}
              placeholder="e.g. CA 123-456"
              required
            />
          </div>
        </div>

        <div className="border-t border-hairline pt-4">
          <h2 className="text-base font-semibold text-navy mb-3">Password</h2>
          <div className="space-y-4">
            <Field label="Password" name="password" type="password" value={form.password} onChange={handleChange} required />
            <Field label="Confirm password" name="password_confirm" type="password" value={form.password_confirm} onChange={handleChange} required />
          </div>
        </div>

        <ConsentCheckboxes value={consent} onChange={setConsent} />

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-2.5"
        >
          {loading ? 'Submitting application…' : 'Apply to drive for Vuna Fresh'}
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

function Field({ label, name, type = 'text', value, onChange, required, placeholder }) {
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
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
    </div>
  );
}
