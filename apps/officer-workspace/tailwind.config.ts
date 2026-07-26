// TEMP: pending dark mode tokens in @openhands/ui
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0d0d0f',
          sidebar: '#131417',
          surface: '#18191c',
          'surface-hover': '#222328',
          border: '#2c2e34',
          'border-subtle': '#222328',
          accent: '#4f46e5',
        },
      },
    },
  },
} satisfies Config;
