export const metadata = { title: 'Privacy policy | Vuna Fresh' };

// Plain-language POPIA notice. The contact address and retention periods
// should be confirmed by Vuna Fresh's Information Officer before launch.
const PRIVACY_EMAIL = 'privacy@vunafresh.co.za';

export default function PrivacyPolicyPage() {
  return (
    <article className="max-w-2xl mx-auto bg-white rounded border border-hairline p-6 sm:p-8 text-sm text-gray-700 leading-relaxed">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Privacy policy</h1>
      <p className="text-xs text-gray-400 mb-6">Last updated 14 October 2026</p>

      <p>
        Vuna Fresh connects buyers with South African farmers and delivers fresh produce. To do that we
        need some personal information. This policy explains what we collect, why, and the rights you have
        under the Protection of Personal Information Act, 2013 (POPIA).
      </p>

      <Section title="What we collect">
        <ul className="list-disc pl-5 space-y-1">
          <li>Your name, email address, phone number and password. Passwords are stored encrypted.</li>
          <li>The addresses you want orders delivered to.</li>
          <li>What you order, what you pay, your payment references and any proof of payment you upload.</li>
          <li>If you buy for a business: its name, type, registration number and credit terms.</li>
          <li>If you farm or drive with us: your farm name and location, or your vehicle details.</li>
          <li>Reviews you write and messages you send to our support team.</li>
        </ul>
      </Section>

      <Section title="Why we use it">
        <ul className="list-disc pl-5 space-y-1">
          <li>To create and run your account, and process and deliver your orders.</li>
          <li>To verify payments, issue invoices and pay farmers their share.</li>
          <li>To send you updates about your orders and support requests.</li>
          <li>To send specials and seasonal news, but only if you said yes to that. You can change your mind any time.</li>
          <li>To meet legal obligations, such as keeping financial records.</li>
        </ul>
      </Section>

      <Section title="Who we share it with">
        <p>We only share what each party needs to fulfil your order:</p>
        <ul className="list-disc pl-5 space-y-1 mt-2">
          <li><strong>Farmers</strong> see the items ordered from them.</li>
          <li><strong>Drivers</strong> see your name, phone number and delivery address for the deliveries assigned to them.</li>
          <li><strong>Service providers</strong> who host our systems and store files, under agreements to keep your information secure.</li>
        </ul>
        <p className="mt-2">We never sell your personal information.</p>
      </Section>

      <Section title="How long we keep it">
        <p>
          We keep your information while your account is active. Financial records (orders, invoices and payments)
          are kept for as long as tax law requires, which is generally five years. When you ask us to delete your
          account, we remove or anonymise everything we are not legally required to keep.
        </p>
      </Section>

      <Section title="Your rights">
        <p>Under POPIA you can:</p>
        <ul className="list-disc pl-5 space-y-1 mt-2">
          <li>ask for a copy of the personal information we hold about you;</li>
          <li>ask us to correct or delete it;</li>
          <li>withdraw consent to marketing at any time;</li>
          <li>object to how we process your information; and</li>
          <li>complain to the Information Regulator (South Africa) at <span className="font-mono">inforeg.org.za</span>.</li>
        </ul>
        <p className="mt-2">
          Once logged in, you can manage marketing consent and request a copy or deletion of your information from
          the <strong>Privacy</strong> page in your account. We respond within 30 days.
        </p>
      </Section>

      <Section title="Security">
        <p>
          Passwords are stored encrypted, connections to our site are encrypted, and only staff who need access to
          your information to do their job can see it. Staff access to personal information is logged.
        </p>
      </Section>

      <Section title="Contact us">
        <p>
          For any privacy question or request, email our Information Officer at{' '}
          <a href={`mailto:${PRIVACY_EMAIL}`} className="text-brand-green font-medium hover:underline">{PRIVACY_EMAIL}</a>.
        </p>
      </Section>
    </article>
  );
}

function Section({ title, children }) {
  return (
    <section className="mt-6">
      <h2 className="text-base font-semibold text-gray-900 mb-2">{title}</h2>
      {children}
    </section>
  );
}
