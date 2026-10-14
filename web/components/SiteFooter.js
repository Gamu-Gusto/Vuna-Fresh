import Link from 'next/link';
import Logo from './Logo';

const COLUMNS = [
  {
    title: 'Buy',
    links: [
      { href: '/products', label: 'Shop produce' },
      { href: '/signup', label: 'Create an account' },
      { href: '/signup?role=business', label: 'Business accounts' },
    ],
  },
  {
    title: 'Grow and deliver',
    links: [
      { href: '/signup?role=farmer', label: 'Sell your produce' },
      { href: '/driver/signup', label: 'Drive with us' },
      { href: '/farmer/login', label: 'Farmer log in' },
      { href: '/driver/login', label: 'Driver log in' },
    ],
  },
  {
    title: 'Help',
    links: [
      { href: '/support', label: 'Report a problem' },
      { href: '/privacy', label: 'Privacy policy' },
    ],
  },
];

export default function SiteFooter() {
  return (
    <footer className="bg-navy text-gray-300 text-sm">
      <div className="max-w-6xl mx-auto px-4 py-12 grid gap-10 sm:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="max-w-xs">
          <Logo className="h-6 w-auto" />
          <p className="mt-4 leading-relaxed">
            Fresh produce from South African farms, ordered direct and delivered to your door.
          </p>
        </div>
        {COLUMNS.map(col => (
          <div key={col.title}>
            <h2 className="text-white font-semibold text-sm mb-3">{col.title}</h2>
            <ul className="space-y-2">
              {col.links.map(l => (
                <li key={l.href}>
                  <Link href={l.href} className="hover:text-white hover:underline underline-offset-4">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10">
        <p className="max-w-6xl mx-auto px-4 py-5 text-xs text-gray-400">© 2026 Vuna Fresh. From the farm to your home.</p>
      </div>
    </footer>
  );
}
