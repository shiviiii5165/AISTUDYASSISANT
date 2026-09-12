# LIVE ROUTE VERIFICATION MATRIX

## 1. Feature Lifecycle & Mounting Verification

Every claimed feature in TeachGenie was tested across seven criteria:
1. **Backend Exists**: Router module and service classes are present in the filesystem.
2. **Mounted**: Router is registered in [`backend/app/main.py`](file:///e:/AISTUDYASSISANT-main/AISTUDYASSISANT-main/backend/app/main.py) and reachable via FastAPI routing table.
3. **Frontend Uses**: Actively invoked by an active page or service in `frontend/src/`.
4. **Deployment Compatible**: Operates cleanly on target platforms (Render Web Service / Vercel Serverless).
5. **No Feature Flag Blocking**: Unrestricted by environment gating.
6. **No Hardcoded Errors**: Free of deliberate 4xx/5xx blocks.
7. **Database Dependencies Valid**: Supabase tables exist and migrate cleanly.

---

## 2. Complete Route Verification Table

| Feature | Backend Path & Router | Mounted Prefix | Frontend Invocations | Deployment Compatibility | Actual Verified Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Advanced Presentation** | `backend/app/api/decks.py` | `/api/decks` | `TopicDeckPage.tsx` (`POST /generate-advanced`, `GET /{id}`) | Compatible (Render & Vercel) | **LIVE** |
| **Legacy Presentation V1** | `backend/app/api/decks.py` | `/api/decks` | None (Orphaned `/outline`, `/expand`, `/render`) | Compatible | **LEGACY / DORMANT** |
| **AI Study Notes Generator**| `backend/app/api/notes_generator.py` | `/api/notes-generator` | `NotesGeneratorPage.tsx` (`notesApi.ts`) | Compatible | **LIVE** |
| **Handwritten OCR Notes** | `backend/app/api/notes.py` | `/api/notes` | Upload modal in Library / Chat | Compatible (Gemini REST) | **PARTIAL** |
| **Lesson Planner** | `backend/app/api/lesson_planner.py`| `/api/lesson-planner` | `LessonPlannerPage.tsx` (`/generate`, `/{id}`, `/publish`)| Compatible | **LIVE** |
| **Lesson Stage Video** | `backend/app/api/lesson_planner.py`| `/api/lesson-planner` | None | **Incompatible** (Returns hardcoded HTTP 400)| **BROKEN / DORMANT** |
| **Diagnostic Quiz** | `backend/app/api/quiz.py` | `/api/quiz` | `QuizGeneratorPage.tsx`, `QuizPage.tsx` (`quizApi.ts`) | Compatible | **LIVE** |
| **Live Classroom Quiz** | `backend/app/api/live_quiz.py` | `/api/live-quizzes` | `LiveQuizHostPage.tsx`, `liveQuizApi.ts` (WebSockets) | Compatible on Render; Poll fallback on Vercel | **LIVE** |
| **Socratic Tutor (TeachMe)**| `backend/app/api/teach.py` | `/api/teach` | `TeachMePage.tsx` (`/start`, `/answer`, `/command`) | Compatible | **LIVE** |
| **Standalone Tutor Agent** | `backend/app/api/tutor.py` | `/api/tutor` | None (Test harness route) | Compatible | **TEST-ONLY** |
| **Standalone Orchestrator** | `backend/app/api/orchestrator.py` | `/api/orchestrator` | None (Test harness route) | Compatible | **TEST-ONLY** |
| **Standalone Librarian** | `backend/app/api/librarian.py` | `/api/librarian` | None (Test harness route) | Compatible | **TEST-ONLY** |
| **Educational Video Engine**| `backend/app/api/lessons.py` | `/api/lessons` | `VideoGeneratorPage.tsx` (`/generate`, `/regenerate-scene`)| Compatible (Requires system FFmpeg) | **LIVE** |
| **PDF Chat & Course RAG** | `backend/app/api/chat.py`, `pdfs.py`| `/chat`, `/pdfs` | `ChatPage.tsx` (`/chat/`, `/pdfs/upload`) | Compatible | **LIVE** |
| **YouTube Recommendations** | `backend/app/api/lesson_planner.py`| `/api/lesson-planner` | `LessonPlannerPage.tsx` (`/youtube-recommendations`) | Compatible | **LIVE** |
| **Extra Learning Materials**| `backend/app/api/lesson_planner.py`| `/api/lesson-planner` | `LessonPlannerPage.tsx` (`/learning-materials`) | Compatible | **LIVE** |
| **Exam Question Predictor** | `backend/app/api/predict.py` | `/api/predict` | No dedicated page; auxiliary modal | Compatible | **BACKEND-ONLY / PARTIAL** |
| **Cashfree Billing** | `backend/app/api/billing.py` | `/api/billing` | `PricingPage.tsx`, `PaymentVerifyPage.tsx` | Compatible | **LIVE** |

---

## 3. Discrepancies Corrected from Previous Audit

1. **The Notes Endpoint Misidentification**:
   - The previous report cited `/api/notes/generate`.
   - **Reality**: The Study Notes Generator is mounted at **`/api/notes-generator/generate`**. `/api/notes` is strictly reserved for handwritten image OCR uploads.
2. **The Live Quiz Endpoint Pluralization**:
   - The previous report cited `/api/live-quiz/`.
   - **Reality**: The router in `backend/app/main.py` is mounted at **`/api/live-quizzes`** (plural).
3. **Dead Stage Video Route**:
   - The route `POST /api/lesson-planner/{id}/stages/{stage_id}/video` exists in `backend/app/api/lesson_planner.py`, but lines 293–300 explicitly return:
     `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Video generation has been removed from lesson planner stages. Use the Video Generator page instead.")`
   - It is not a live feature; it is an intentionally decommissioned legacy route.
