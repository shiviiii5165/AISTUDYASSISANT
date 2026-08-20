import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'sans-serif'],
      },
      colors: {
        cream: {
          50: '#FAFAF8',
          100: '#F3F0EA',
          200: '#E8E3DA',
        },
        sage: {
          500: '#16A34A',
          600: '#15803D',
          50: '#DCFCE7',
        },
        amber: {
          400: '#FBBF24',
          500: '#F59E0B',
          50: '#FEF3C7',
        },
        ai: {
          500: '#6366F1',
          50: '#EEF2FF',
        }
      }
    }
  },
  plugins: [],
} satisfies Config
