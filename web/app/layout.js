import './globals.css';
import { Archivo } from 'next/font/google';
import { AuthProvider } from '@/lib/auth-context';

// Variable width axis: condensed for headlines (echoing the logo), normal for text.
const archivo = Archivo({
  subsets: ['latin'],
  axes: ['wdth'],
  variable: '--font-archivo',
  display: 'swap',
});

export const metadata = {
  title: 'Vuna Fresh: fresh produce straight from South African farms',
  description: 'Order fruit and vegetables directly from local farmers, for your home, restaurant or spaza shop. Delivered to your door.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={archivo.variable}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
