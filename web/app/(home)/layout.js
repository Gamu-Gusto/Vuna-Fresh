import Nav from '@/components/Nav';
import SiteFooter from '@/components/SiteFooter';
import { CartProvider } from '@/lib/cart-context';

// The homepage runs full-bleed sections, so it skips the buyer layout's
// centred content container.
export default function HomeLayout({ children }) {
  return (
    <CartProvider>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </div>
    </CartProvider>
  );
}
