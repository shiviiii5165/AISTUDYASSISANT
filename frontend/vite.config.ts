import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '../',
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/pdfs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        bypass(req) {
          // Exact /chat path is a React Router SPA route — let Vite serve index.html.
          // Sub-paths like /chat/123/messages are backend API calls and pass through.
          if (req.url === '/chat' || req.url === '/chat/') return req.url;
        },
      },
    },
  },
})
