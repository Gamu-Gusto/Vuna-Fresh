import Link from 'next/link';
import Logo from './Logo';

// Slim branded header for the farmer, driver and admin sign-in pages, which
// sit outside the buyer layout. The logo always leads back to the homepage.
export default function AuthHeader() {
  return (
    <header className="bg-navy">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center">
        <Link href="/" aria-label="Vuna Fresh home"><Logo /></Link>
      </div>
    </header>
  );
}
