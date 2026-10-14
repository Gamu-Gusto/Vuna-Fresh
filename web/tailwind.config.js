/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          // Field green: buttons, links and prices on light backgrounds.
          // Deeper than the logo green so white text passes WCAG AA (5.4:1).
          green: '#2F7A2C',
          light: '#276A25', // hover/pressed state of brand-green
          bg: '#F5F6F4',
        },
        // Logo green: only on navy, where it passes contrast.
        sprout: '#4AAE45',
        // Price chalk on the navy market board. Only used there.
        maize: '#F3C64B',
        navy: '#0F1F3D',
        leaf: '#E7F3E4',
        ember: '#C1442E',
        hairline: '#D6DCE8',
      },
      // One family (Archivo), two widths: condensed for headlines, normal for UI.
      // `mono` is kept as an alias so existing numeric spans get tabular figures
      // in the body face instead of a monospace font (see globals.css).
      fontFamily: {
        heading: ['var(--font-archivo)', 'sans-serif'],
        sans: ['var(--font-archivo)', 'sans-serif'],
        mono: ['var(--font-archivo)', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
