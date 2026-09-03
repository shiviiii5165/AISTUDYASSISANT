import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Lora', 'Georgia', 'serif'],
        hindi:   ['Noto Sans Devanagari', 'Inter', 'sans-serif'],
      },
      colors: {
        brand: {
          navy: '#091540',
          royal: '#1B2CC1',
          periwinkle: '#7692FF',
          baby: '#ABD2FA',
          cream: '#FAFAF8',
        },
        surface: {
          DEFAULT: '#FAFAF8',
          card: '#FFFFFF',
          navy: '#091540',
        },
        ink: {
          DEFAULT: '#091540',
          muted: '#6B7280',
          inverse: '#FFFFFF',
        }
      },
      boxShadow: {
        'bento': '0 4px 20px -2px rgba(9, 21, 64, 0.05), 0 2px 8px -2px rgba(9, 21, 64, 0.03)',
        'bento-hover': '0 12px 30px -4px rgba(27, 44, 193, 0.12), 0 4px 12px -4px rgba(27, 44, 193, 0.08)',
      },
      borderRadius: {
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
      },
    }
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config
