# LearnByGenie

> **LearnByGenie** (formerly TeachGenie) — An enterprise-grade AI study assistant and smart classroom assessment platform.

## Features

- **LearnByGenie Live Quiz**: Low-latency, high-concurrency real-time classroom assessment engine with server-authoritative timers, IndexedDB write-ahead answer journals, anti-tampering progression tokens, and instant student lockout.
- **LearnByGenie AI Notes**: Pedagogically structured, syllabus-grounded educational notes generation engine with strict LaTeX/notation QA, deterministic curriculum alignment, and PDF export.
- **LearnByGenie Lesson Planner**: Adaptive pedagogical curriculum roadmaps, YouTube precision alignment, and diagnostic invariant exercises.
- **LearnByGenie PPT Generator**: Clean educational presentation engine with deterministic archetype layouts, bundled thematic icons, and structured visual planning.
- **LearnByGenie AI Tutor**: Grounded question answering from uploaded PDF course material without hallucinations.

## Technology Stack

- **Backend**: FastAPI (Python 3.11), Supabase PostgreSQL, Pydantic v2
- **Frontend**: React 19, TypeScript, Vite, TailwindCSS, Framer Motion
- **Persistence & Realtime**: Supabase Database, Supabase Auth, IndexedDB (client journal)
