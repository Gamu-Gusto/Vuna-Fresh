import Link from 'next/link';
import HarvestBoard from '@/components/HarvestBoard';

const STEPS = [
  {
    title: 'Choose your produce',
    text: 'Browse what local farms are harvesting this week, with each farm’s own price.',
  },
  {
    title: 'Pay by EFT',
    text: 'Pay into our bank account with your order reference, then upload your proof of payment.',
  },
  {
    title: 'The farm packs, we deliver',
    text: 'Once your payment is confirmed the farm prepares your order and a driver brings it to your door.',
  },
];

const AUDIENCES = [
  {
    title: 'For your home',
    text: 'Weekly vegetables and fruit for the family, without the supermarket mark-up. Set up a regular delivery of the things you always buy.',
    link: { href: '/signup', label: 'Create a household account' },
  },
  {
    title: 'For restaurants, retailers and spaza shops',
    text: 'Order in bulk from several farms in one go. Approved businesses can buy on 7, 14 or 30-day terms and pay by invoice.',
    link: { href: '/signup?role=business', label: 'Open a business account' },
  },
  {
    title: 'For farmers',
    text: 'List what you’re harvesting and sell straight to buyers in your area. You see every order and get paid your share once the buyer has paid.',
    link: { href: '/signup?role=farmer', label: 'Start selling' },
  },
];

export default function HomePage() {
  return (
    <>
      {/* Hero: what it is, who it's for, why it matters, what to do — all above the fold */}
      <section className="bg-navy text-white">
        <div className="max-w-6xl mx-auto px-4 pt-10 pb-14 sm:pt-16 sm:pb-20 grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-center">
          <div>
            <h1 className="type-display text-white text-[2.75rem] min-[400px]:text-[3.25rem] sm:text-7xl lg:text-[4.5rem] xl:text-[4.75rem]">
              {/* Break by phrase; automatic balancing strands "straight" on its own line */}
              <span className="block">Fresh produce</span>
              <span className="block">straight from</span>
              <span className="block">South African farms.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-gray-300">
              Order directly from the farmers who grow it, for your home, your restaurant or your spaza shop.
              Fewer middlemen means fresher food for you and a fairer price for the farm.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-4">
              <Link href="/products" className="btn-primary px-6 py-3.5 text-base">
                Shop this week&apos;s produce
              </Link>
              <Link href="/signup?role=farmer" className="text-base font-semibold text-sprout hover:text-white underline-offset-4 hover:underline">
                I&apos;m a farmer and want to sell
              </Link>
            </div>
            <p className="mt-6 text-sm text-gray-400">Pay by EFT. Delivered to your door.</p>
          </div>

          <HarvestBoard />
        </div>
      </section>

      {/* A real sequence, so the numbers carry meaning */}
      <section className="max-w-6xl mx-auto px-4 py-16 sm:py-20">
        <h2 className="type-display text-4xl sm:text-5xl">How ordering works</h2>
        <ol className="mt-10 grid gap-10 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="border-t-2 border-navy pt-5">
              <span className="type-display text-5xl text-brand-green font-mono" aria-hidden="true">{i + 1}</span>
              <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
              <p className="mt-2 text-gray-600 leading-relaxed max-w-sm">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-white border-y border-hairline">
        <div className="max-w-6xl mx-auto px-4 py-16 sm:py-20">
          <h2 className="type-display text-4xl sm:text-5xl max-w-2xl">Who Vuna Fresh is for</h2>
          <div className="mt-10 grid gap-x-12 gap-y-10 md:grid-cols-3">
            {AUDIENCES.map(a => (
              <div key={a.title}>
                <h3 className="text-xl font-semibold">{a.title}</h3>
                <p className="mt-2 text-gray-600 leading-relaxed">{a.text}</p>
                <Link href={a.link.href} className="mt-4 inline-block font-semibold text-brand-green hover:text-brand-light underline underline-offset-4 decoration-2">
                  {a.link.label}
                </Link>
              </div>
            ))}
          </div>
          <p className="mt-12 text-gray-600">
            Have a bakkie or a car and some free days?{' '}
            <Link href="/driver/signup" className="font-semibold text-brand-green underline underline-offset-4">Apply to drive deliveries</Link>.
          </p>
        </div>
      </section>
    </>
  );
}
