# REPOSITORY TRUTH: VERIFIED ARCHITECTURAL BASELINE

## 1. Resolution of Frontend Stack Contradiction

### Verified Facts (Ground Truth)
- **CURRENT FRONTEND FRAMEWORK**: **React 19** (`"react": "^19.2.6"`, `"react-dom": "^19.2.6"`)
- **CURRENT BUILD SYSTEM**: **Vite 8** (`"vite": "^8.0.12"`, `"@vitejs/plugin-react": "^6.0.1"`)
- **CURRENT ROUTER**: **React Router DOM v7** (`"react-router-dom": "^7.17.0"`) (Client-Side SPA routing)
- **CURRENT CSS SYSTEM**: **Tailwind CSS v3.4.19** with `@tailwindcss/typography` and PostCSS 8

### Why The Previous Audit Claimed "Next.js App Router":
The previous audit report incorrectly asserted that TeachGenie used "Next.js App Router". This was a **hallucinated assumption** made by an LLM relying on common contemporary web patterns rather than inspecting `frontend/package.json`.
- There is **no `next.config.js` or `next.config.mjs`** anywhere in the repository.
- There is **no `app/` directory** with Next.js conventions (`page.tsx`, `layout.tsx`, `route.ts`).
- Routing is defined entirely in [`frontend/src/App.tsx`](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/frontend/src/App.tsx) using standard `<BrowserRouter>`, `<Routes>`, and `<Route>` components from `react-router-dom`.

---

## 2. Evidence from Configuration Files

### A. `frontend/package.json` Dependencies & Scripts
```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "@cashfreepayments/cashfree-js": "^1.0.7",
    "@radix-ui/react-dropdown-menu": "^2.1.24",
    "@supabase/supabase-js": "^2.108.2",
    "axios": "^1.18.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "framer-motion": "^12.40.0",
    "lucide-react": "^1.20.0",
    "react": "^19.2.6",
    "react-dom": "^19.2.6",
    "react-dropzone": "^15.0.0",
    "react-helmet-async": "^3.0.0",
    "react-hot-toast": "^2.6.0",
    "react-markdown": "^10.1.0",
    "react-router-dom": "^7.17.0",
    "recharts": "^3.8.1",
    "remark-gfm": "^4.0.1",
    "tailwind-merge": "^3.6.0",
    "zustand": "^5.0.14"
  },
  "devDependencies": {
    "@tailwindcss/typography": "^0.5.20",
    "@types/react": "^19.2.14",
    "@vitejs/plugin-react": "^6.0.1",
    "tailwindcss": "^3.4.19",
    "typescript": "~6.0.2",
    "vite": "^8.0.12"
  }
}
```

### B. `frontend/vite.config.ts`
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
          if (req.url === '/chat' || req.url === '/chat/') return req.url;
        },
      },
    },
  },
})
```

---

## 3. Directory Structure Truth

```text
E:\AISTUDYASSISANT-main\AISTUDYASSISANT-main
├── api/
│   └── index.py                    # Vercel Serverless Function entrypoint (wraps backend/app/main.py)
├── backend/
│   ├── app/
│   │   ├── api/                    # Mounted FastAPI routers
│   │   ├── core/                   # Config, security, logging
│   │   ├── db/                     # Supabase client & migrations
│   │   └── services/
│   │       ├── ai/                 # ModelRouter, circuit breaker, provider adapters
│   │       ├── live_quiz/          # WebSocket session manager, scoring
│   │       ├── notes/              # NotesContextAnalyzer, decision, generator
│   │       ├── presentation/       # TopicOntologyAgent, PlannerAgent, ContentAgent, ReviewerAgent
│   │       ├── teach/              # Mastery, TeacherAgent, AssessmentAgent, Orchestrator
│   │       ├── video/              # Planner, TTS, Compositor, Graphics, Stock
│   │       └── lesson_planner/     # Adapters, learning materials
│   └── tests/                      # 543 unit & integration test files
├── frontend/
│   ├── public/                     # Static icons, favicons, OG images
│   ├── src/
│   │   ├── components/             # Reusable UI widgets, AppLayout
│   │   ├── lib/                    # API clients (api.ts, notesApi.ts, quizApi.ts, liveQuizApi.ts)
│   │   ├── pages/                  # 19 SPA view components
│   │   ├── store/                  # Zustand global state stores
│   │   ├── App.tsx                 # React Router DOM v7 route definitions
│   │   └── main.tsx                # React 19 root mounting
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
├── render.yaml                     # Render deployment configuration
└── vercel.json                     # Vercel frontend & serverless routing configuration
```

---

## 4. Deployment Configuration Truth

1. **Frontend**: Deployed via **Vercel** or **Render Static Site**. `vercel.json` rewrites all non-API paths to `/index.html` for client-side SPA routing.
2. **Backend**: 
   - **Render Web Service**: Ran via `uvicorn app.main:app --host 0.0.0.0 --port 8000` (defined in `Procfile` and `render.yaml`).
   - **Vercel Serverless Function**: Proxied via `api/index.py` which loads `backend/app/main.py:app`.
