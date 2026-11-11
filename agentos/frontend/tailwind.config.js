/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#003087',
          50: '#e6edf8',
          100: '#c0d2ee',
          600: '#003087',
          700: '#00266e',
          800: '#001d55',
          900: '#001040',
        },
        paypal: {
          DEFAULT: '#0070BA',
          50: '#e0f0fb',
          100: '#b3d9f4',
          500: '#0070BA',
          600: '#005ea0',
          700: '#004d85',
        },
        amber: {
          DEFAULT: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
      },
    },
  },
  plugins: [
    // @tailwindcss/forms provides nicer form defaults
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@tailwindcss/forms'),
  ],
}
