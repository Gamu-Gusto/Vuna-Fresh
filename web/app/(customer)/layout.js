import Nav from '@/components/Nav';
import SiteFooter from '@/components/SiteFooter';
import { CartProvider } from '@/lib/cart-context';

export default function BuyerLayout({ children }) {
  return (
    <CartProvider>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8 sm:py-10">
          {children}
        </main>
        <SiteFooter />
      </div>
    </CartProvider>
  );
}
