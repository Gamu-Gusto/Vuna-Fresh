'use client';

import { Suspense, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import ConsentCheckboxes, { INITIAL_CONSENT } from '@/components/ConsentCheckboxes';

const ROLES = [
  { value: 'customer', label: 'Household', hint: 'Fresh produce for my home' },
  { value: 'business', label: 'Business', hint: 'Restaurant, retailer or spaza shop' },
  { value: 'farmer', label: 'Farmer', hint: 'I want to sell my produce' },
];

const BUSINESS_TYPES = [
  { value: 'retailer', label: 'Retailer' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'spaza_shop', label: 'Spaza shop' },
  { value: 'other', label: 'Other' },
];

const CREDIT_TERMS = [
  { value: 'prepaid', label: 'Prepaid' },
  { value: 'net_7', label: 'Net 7' },
  { value: 'net_14', label: 'Net 14' },
  { value: 'net_30', label: 'Net 30' },
];

// useSearchParams() needs a Suspense boundary or the production build fails to prerender.
export default function SignupPage() {
  return (
    <Suspense>
      <SignupPageContent />
    </Suspense>
  );
}

function SignupPageContent() {
  const { register, registerBusiness } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialRole = searchParams.get('role');

  const [role, setRole] = useState(ROLES.some(r => r.value === initialRole) ? initialRole : 'customer');
  const [shared, setShared] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    password: '', password_confirm: '',
  });
  const [address, setAddress] = useState({
    street_address: '', suburb: '', city: '', province: '', postal_code: '',
  });
  const [farmer, setFarmer] = useState({ farm_name: '', farm_location: '' });
  const [business, setBusiness] = useState({
    business_name: '', business_type: 'retailer', credit_terms: 'prepaid',
  });

  const [consent, setConsent] = useState(INITIAL_CONSENT);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function updateField(setter) {
    return e => {
      const { name, value } = e.target;
      setter(f => ({ ...f, [name]: value }));
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (role === 'business') {
        await registerBusiness({
          ...shared,
          ...consent,
          ...address,
          business_name: business.business_name,
          business_type: business.business_type,
          credit_terms: business.credit_terms,
        });
        router.push('/business/pending');
      } else {
        const fields = { ...shared, ...consent, role };
        if (role === 'farmer') {
          fields.farm_name = farmer.farm_name;
          fields.farm_location = farmer.farm_location;
        }
        await register(fields);
        await apiClient.post('/users/me/addresses/', { ...address, is_default: true });
        router.push(role === 'farmer' ? '/farmer/pending' : '/products');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto pb-6">
      <h1 className="type-display text-5xl">Create your account</h1>
      <p className="mt-2 mb-6 text-gray-600">Who are you buying or selling for?</p>

      <fieldset className="mb-8">
        <legend className="sr-only">Account type</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {ROLES.map(r => (
            <label
              key={r.value}
              className={`cursor-pointer rounded-md border-2 px-4 py-3 transition-colors ${
                role === r.value ? 'border-brand-green bg-white' : 'border-hairline bg-white/60 hover:border-gray-400'
              }`}
            >
              <input
                type="radio"
                name="role"
                value={r.value}
                checked={role === r.value}
                onChange={() => setRole(r.value)}
                className="sr-only"
              />
              <span className="block font-semibold text-navy">{r.label}</span>
              <span className="block text-sm text-gray-500 leading-snug">{r.hint}</span>
            </label>
          ))}
        </div>
        {role !== 'customer' && (
          <p className="mt-3 text-sm text-gray-600">
            {role === 'farmer' ? 'Farm accounts are checked by our team before you can list produce.' : 'Business accounts are checked by our team before you can order on credit terms.'}
          </p>
        )}
      </fieldset>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded border border-hairline p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name" name="first_name" value={shared.first_name} onChange={updateField(setShared)} required />
          <Field label="Last name" name="last_name" value={shared.last_name} onChange={updateField(setShared)} required />
        </div>
        <Field label="Email" name="email" type="email" value={shared.email} onChange={updateField(setShared)} required />
        <Field label="Phone" name="phone" type="tel" value={shared.phone} onChange={updateField(setShared)} required={role !== 'customer'} />
        <Field label="Password" name="password" type="password" value={shared.password} onChange={updateField(setShared)} required />
        <Field label="Confirm password" name="password_confirm" type="password" value={shared.password_confirm} onChange={updateField(setShared)} required />

        <div className="border-t border-hairline pt-4">
          <h2 className="text-base font-semibold text-navy mb-3">Delivery address</h2>
          <div className="space-y-4">
            <Field label="Street address" name="street_address" value={address.street_address} onChange={updateField(setAddress)} required />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Suburb (optional)" name="suburb" value={address.suburb} onChange={updateField(setAddress)} />
              <Field label="City" name="city" value={address.city} onChange={updateField(setAddress)} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Province" name="province" value={address.province} onChange={updateField(setAddress)} required />
              <Field label="Postal code" name="postal_code" value={address.postal_code} onChange={updateField(setAddress)} required />
            </div>
          </div>
        </div>

        {role === 'farmer' && (
          <div className="border-t border-hairline pt-4">
            <h2 className="text-base font-semibold text-navy mb-3">Farm details</h2>
            <div className="space-y-4">
              <Field label="Farm name" name="farm_name" value={farmer.farm_name} onChange={updateField(setFarmer)} required />
              <Field
                label="Farm location"
                name="farm_location"
                value={farmer.farm_location}
                onChange={updateField(setFarmer)}
                placeholder="e.g. Stellenbosch, Western Cape"
              />
            </div>
          </div>
        )}

        {role === 'business' && (
          <div className="border-t border-hairline pt-4">
            <h2 className="text-base font-semibold text-navy mb-3">Business details</h2>
            <div className="space-y-4">
              <Field label="Business name" name="business_name" value={business.business_name} onChange={updateField(setBusiness)} required />
              <div>
                <label htmlFor="business_type" className="block text-sm font-medium text-gray-700 mb-1">Business type</label>
                <select
                  id="business_type"
                  name="business_type"
                  value={business.business_type}
                  onChange={updateField(setBusiness)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
                >
                  {BUSINESS_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="credit_terms" className="block text-sm font-medium text-gray-700 mb-1">Requested credit terms</label>
                <select
                  id="credit_terms"
                  name="credit_terms"
                  value={business.credit_terms}
                  onChange={updateField(setBusiness)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
                >
                  {CREDIT_TERMS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
          </div>
        )}

        <ConsentCheckboxes value={consent} onChange={setConsent} />

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-2.5"
        >
          {loading ? 'Creating account…' : 'Sign up'}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-gray-500">
        Already have an account?{' '}
        <Link href="/login" className="text-brand-green font-medium hover:underline">
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
