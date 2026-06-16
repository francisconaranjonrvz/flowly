/** @type {import('tailwindcss').Config} */
// Flowly — Tailwind v3 (binario standalone, sin Node).
// Colores semánticos (estilo Material-3) mapeados a variables CSS de
// static/css/design-system.css. Las 4 variantes de marca/tema
// (Flowly claro/oscuro, NSW oscuro/claro) cambian esas variables vía
// [data-brand] y [data-theme] en <html>, sin recompilar.
// Preflight desactivado: el reset vive en design-system.css.
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--surface) / <alpha-value>)',
        surface: {
          DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
          container: 'rgb(var(--surface-container) / <alpha-value>)',
          'container-low': 'rgb(var(--surface-container-low) / <alpha-value>)',
          'container-high': 'rgb(var(--surface-container-high) / <alpha-value>)',
          variant: 'rgb(var(--surface-variant) / <alpha-value>)',
        },
        'on-surface': {
          DEFAULT: 'rgb(var(--on-surface) / <alpha-value>)',
          variant: 'rgb(var(--on-surface-variant) / <alpha-value>)',
        },
        outline: {
          DEFAULT: 'rgb(var(--outline) / <alpha-value>)',
          variant: 'rgb(var(--outline-variant) / <alpha-value>)',
        },
        primary: {
          DEFAULT: 'rgb(var(--primary) / <alpha-value>)',
          container: 'rgb(var(--primary-container) / <alpha-value>)',
        },
        'on-primary': 'rgb(var(--on-primary) / <alpha-value>)',
        accent: 'rgb(var(--accent-text) / <alpha-value>)',
        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        danger: 'rgb(var(--error) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        mulish: ['Mulish', 'Inter', 'sans-serif'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '8px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      boxShadow: {
        glow: '0 0 15px rgb(var(--primary) / 0.25)',
        card: '0 1px 3px rgb(var(--shadow-color) / 0.12)',
        // Sombra simétrica suave solo para overlays flotantes (menús/dropdowns).
        lift: '0 6px 20px rgb(var(--shadow-color) / 0.14)',
      },
    },
  },
  plugins: [],
}
