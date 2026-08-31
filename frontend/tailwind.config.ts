import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
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
        },
        surface: {
          DEFAULT: '#FAF9F6',
          card: '#FFFFFF',
        },
        ink: {
          DEFAULT: '#1E1B2E',
          muted: '#6B7280',
        },
        genie: {
          purple: {
            DEFAULT: '#6D28D9',
            soft: '#EDE9FE',
          },
          amber: {
            DEFAULT: '#F59E0B',
            soft: '#FEF3C7',
          }
        },
        border: {
          soft: '#E9E7F0',
        }
      }
    }
  },
  plugins: [],
} satisfies Config
