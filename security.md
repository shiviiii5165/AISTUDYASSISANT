# Security & Correctness Audit — TeachGenie
Audit date: 2026-08-31
Scope: full repo post-reorg. Relevant reorg commits: `314cbe8` (relocate tests/scripts),
`7695fea` (consolidate migrations to `backend/migrations/`), `27ec146` (remove orphaned dead code),
`02eed7a` (delete render artifacts, gitignore `scratch/`), `06c1f61` (remove old paths).
Billing (`billing.py`, `frontend/src/services/billing.ts`, PricingPage, PaymentVerifyPage) explicitly
out of scope per project owner — not yet in production use.

Read-only pass. No files were modified.

## Summary

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High     | 5 |
| Medium   | 8 |
| Low      | 5 |
| **Total**| **19** |

> Update (fix pass follow-up): one additional finding — [MEDIUM] IDOR on the
> video-lesson delete route via `PROJECT_STORE` — was identified while fixing the
> [HIGH] `PROJECT_STORE` read IDOR (same bug class, different route/method) and is
> recorded below. Medium count 7→8, total 18→19.

The application backend runs entirely under the Supabase **service-role key**
(`.env.example:5`, `SUPABASE_KEY=your_supabase_service_role_key`; used unconditionally in
`backend/app/db/supabase_client.py:5`). The service role bypasses all Postgres Row-Level Security.
Every RLS policy defined in `backend/migrations/` (on `pdfs`, `quiz_scores`, `learning_roadmaps`,
`roadmap_stages`, `topic_decks`, `daily_usage`, etc.) is therefore **inert for all backend-issued
queries** and provides no backstop whatsoever. Data isolation depends 100% on application-layer
`.eq("user_id", ...)` filters — and several code paths omit that filter, query in-memory caches
that are not user-scoped, or expose whole endpoints with no authentication at all. A second
structural weakness: five multi-agent endpoints ship with no auth dependency, and all four plan/quota
"guards" are unconditional pass-throughs while the quota-tracking SQL functions are never called from
anywhere in the codebase. The posture is not production-ready: cross-tenant reads of another user's
uploaded document content are reachable today by any logged-in user, and unauthenticated abuse of
LLM-backed endpoints is reachable by anyone on the internet.

## Findings

### [CRITICAL] Five agent endpoints have no authentication
- **Location**:
  - `backend/app/api/orchestrator.py:30-41` (`POST /api/orchestrator/route`)
  - `backend/app/api/librarian.py:26-27` (`POST /api/librarian/retrieve`)
  - `backend/app/api/tutor.py:36-37` (`POST /api/tutor/turn`)
  - `backend/app/api/content_creator.py:14-30` (`POST /api/content-creator/generate`)
  - `backend/app/api/content_creator.py:33-43` (`GET /api/content-creator/status/{job_id}`)
  - All five are mounted in production in `backend/app/main.py:70-77`.
- **What it is**: None of these route handlers declare `Depends(get_current_user)` or any other
  auth dependency. The request models (`OrchestratorRequest`, `LibrarianRequest`, `TutorRequest`,
  `ContentRequest`) carry no verified identity. `create_content` / `classify_and_route` / the tutor
  and librarian agents all invoke paid LLM providers (Gemini/Groq/OpenRouter) on each call.
- **What it affects**: Anyone on the internet can drive unmetered LLM calls (direct financial loss
  and a trivial cost-amplification / DoS vector). `GET /content-creator/status/{job_id}` returns the
  full `ContentCreatorOutput` for any job id with no ownership check (`content_creator.py:39-43`),
  exposing another user's generated content/flashcards if the job id is known or brute-forced.
- **Trigger conditions**: No auth. A single unauthenticated HTTP request. `/route`, `/retrieve`,
  `/turn`, `/generate` are directly reachable; the status IDOR additionally needs a job id (UUID).
- **Verified / Unverified**: Verified from route definitions and `main.py` registration. The docstring
  in `orchestrator.py:6-9` claims the endpoint is "purely for independent testing… before wiring it
  in," but it is registered in the production app.

---

### [HIGH] Cross-tenant document read via Exam Predictor (`get_top_chunks` has no user filter)
- **Location**: `backend/app/api/predict.py:58-72` (`POST /api/predict/exam-questions`);
  `backend/app/services/vector_service.py:97-113` (`get_all_chunks_text`);
  RPC definition `backend/migrations/006_fix_missing_schema.sql:49-58` (`get_top_chunks`).
- **What it is**: The endpoint takes a client-supplied `pdfId` and calls
  `get_all_chunks_text(request.pdfId)` → RPC `get_top_chunks(match_pdf_id, match_count)`. The RPC
  body filters `WHERE dc.pdf_id = match_pdf_id` **only** — no `user_id`/ownership join. The endpoint
  never verifies that `request.pdfId` belongs to `current_user`. Because the backend uses the
  service-role key, RLS does not constrain this.
- **What it affects**: Full chunk text (i.e. the extracted content) of any other user's uploaded
  PDF/handwritten note, returned indirectly as predicted-question context.
- **Trigger conditions**: A valid (any-tier) account plus a target `pdf_id`. `pdf_id` is a random
  UUID (`pdfs.py:19`), so it is not enumerable, but it is leakable (URLs, logs, referrals).
- **Verified / Unverified**: Verified end-to-end (endpoint → service → RPC SQL). No ownership check
  exists on any hop.

### [HIGH] Cross-tenant document read via chat "global" modes (`get_all_chunks` ignores `user_id`)
- **Location**: `backend/app/services/vector_store.py:57-81` (`get_all_chunks`);
  called from `backend/app/services/rag_service.py:172`; reached via
  `backend/app/api/chat.py:9-22` (`POST /chat/ask`).
- **What it is**: `get_all_chunks(pdf_id, user_id)` accepts `user_id` but the query filters by
  `.eq("pdf_id", pdf_id)` only (line 65) — `user_id` is unused. The in-code comment at lines 60-62
  claims "We explicitly filter by both to be extremely safe," which is false. This path is taken
  whenever `mode != "Quick Answer"` (`rag_service.py:168,172`) — i.e. all of "Full Chapter Crux",
  "No Fact Miss", "Formula Coverage", "Exam Shield Notes", "Generate MCQs", "Predicted Exam
  Questions", "Kid/Student/University/Professor Mode". By contrast `search_relevant_chunks`
  (used only for "Quick Answer") routes through RPC `match_document_chunks`, which **does** join
  `pdfs p ON p.id = dc.pdf_id AND p.user_id = filter_user_id` (`006_fix_missing_schema.sql:83-86`) —
  so only Quick Answer is protected.
- **What it affects**: Full chunk text of any other user's PDF, returned as the chat answer/sources.
- **Trigger conditions**: A valid account, any non-"Quick Answer" mode, plus a target `pdf_id` (UUID).
- **Verified / Unverified**: Verified. The `user_id` argument is passed but demonstrably dropped.

### [HIGH] IDOR on video lessons via in-memory `PROJECT_STORE` (ownership check bypassed)
- **Location**: `backend/app/api/lessons.py:152-194` (`GET /api/lessons/{lesson_id}`), specifically
  the `if lesson_id in PROJECT_STORE:` branch at lines 161-173.
- **What it is**: The handler returns the full project (storyboard, transcript, video URL, metrics)
  straight from the process-memory `PROJECT_STORE` dict keyed by `lesson_id` with **no** `user_id`
  comparison. Only the Supabase fallback path (lines 176-190) applies `.eq("user_id", ...)`. Any
  lesson currently held in memory is readable by any authenticated user who knows/guesses its id.
- **What it affects**: Another user's generated video lesson content and its signed video URL.
- **Trigger conditions**: A valid account plus a `lesson_id` that is currently resident in
  `PROJECT_STORE` (i.e. recently active on that worker). `lesson_id` is a UUID.
- **Verified / Unverified**: Verified from the branch logic. Reachability is per-worker and
  time-bounded (memory only), which is why this is High rather than Critical.

### [MEDIUM] IDOR on the video-lesson delete route via `PROJECT_STORE` (in-memory delete not ownership-checked)
- **Location**: `backend/app/api/lessons.py:233-243` (`DELETE /api/lessons/{lesson_id}`),
  specifically the unconditional `if lesson_id in PROJECT_STORE: del PROJECT_STORE[lesson_id]`
  at lines 241-242.
- **What it is**: The database delete on line 238 is correctly scoped
  (`.eq("id", lesson_id).eq("user_id", current_user.id)`), but the subsequent in-memory
  deletion removes the entry from the process-wide `PROJECT_STORE` dict with **no** check that
  `PROJECT_STORE[lesson_id].user_id == current_user.id`. Any authenticated user can therefore
  evict another user's in-memory lesson project by calling delete with its `lesson_id`.
- **What it affects**: Availability/integrity of another user's *in-flight or recently active*
  video-lesson project held in worker memory. The persisted `video_lessons` row is not affected
  (the DB delete is user-scoped), so the impact is disruption of an active generation / loss of the
  in-memory active state, not permanent data destruction.
- **Trigger conditions**: A valid (any-tier) account plus a `lesson_id` (UUID) currently resident in
  that worker's `PROJECT_STORE`. Per-worker and time-bounded, like the read variant.
- **Verified / Unverified**: Verified from the route logic. Same bug class as the [HIGH]
  `PROJECT_STORE` read IDOR (the read branch at `lessons.py:161-173` was fixed with an ownership
  check during the fix pass; this delete branch was intentionally left untouched as it was outside
  that finding's cited location). Rated Medium rather than High because the impact is contained and
  recoverable (in-memory only; the user can regenerate), whereas the read variant exposed content.

### [HIGH] IDOR on lesson-planner roadmaps via `_MEMORY_ROADMAPS` cache (ownership check bypassed)
- **Location**: `backend/app/api/lesson_planner.py:131-134` (`_get_roadmap`), consumed by
  `GET /api/lesson-planner/{roadmap_id}` (`:211-221`) and every `/{roadmap_id}/...` sub-route
  (`:223,297,320,343,368,403,419,434,459,483,507,531,551`).
- **What it is**: `_get_roadmap(roadmap_id, user_id)` checks the module-level `_MEMORY_ROADMAPS`
  dict **first** (line 133) and returns the cached roadmap with no `user_id` check. `_save_roadmap`
  (`:87-88`) populates that dict keyed only by `roadmap.id`, for all users. The Supabase branch
  (line 138) does filter by `user_id`, but it is only reached on a cache miss.
- **What it affects**: Another user's roadmap (topic, stages, generated content) and any mutating
  sub-route that resolves the roadmap through this helper (edit/reorder/merge/split/publish/generate
  PPT/video/quiz/notes on someone else's roadmap).
- **Trigger conditions**: A valid account plus a `roadmap_id` (UUID) currently in the worker's memory.
- **Verified / Unverified**: Verified. Same bug class as the `PROJECT_STORE` finding above.

### [HIGH] Plan/quota enforcement is entirely absent (guards are no-ops; quota SQL never called)
- **Location**: `backend/app/core/plan_guards.py:5-19` (all four functions);
  quota functions defined but never invoked: `increment_daily_usage`
  (`backend/migrations/005_pricing.sql:24`) and `increment_monthly_deck_usage`
  (`backend/migrations/002_decks.sql:50`) — a repo-wide grep finds call sites only inside the two
  `.sql` files, never in `backend/app/`.
- **What it is**: `require_pro`, `check_daily_question_limit`, `check_pdf_upload_limit`,
  `check_topic_deck_limit` each just `return current_user` ("Allow all users for now"). Endpoints
  that depend on them for gating get no gating. The `daily_usage` / `monthly_deck_usage` tables and
  their atomic increment RPCs exist in the schema but are dead — nothing in the app increments or
  checks them.
- **What it affects**: Every "pro"/quota-gated surface. Dependent endpoints include:
  `chat.py:10,14` (daily-question + pro modes), `predict.py:61` (`require_pro`), `notes.py:32`
  (`require_pro`), `decks.py:50,51,185,186` (pro + deck limit), `lessons.py:41`
  (`check_daily_question_limit`), `teach.py:30,76,103,130` (`check_daily_question_limit`).
- **Trigger conditions**: Any authenticated user; no precondition — pro features and unlimited usage
  are free to everyone.
- **Verified / Unverified**: Verified (stub bodies + absent call sites).
- **If billing goes live as-is**: This becomes the primary revenue-loss / paywall-bypass vector —
  effectively Critical, since the entitlement layer it would rely on does not exist.

---

### [MEDIUM] Request-size limit bypassable by omitting Content-Length
- **Location**: `backend/app/core/security.py:39-51`; configured at
  `backend/app/main.py:26` (`max_size_bytes=10_000_000`).
- **What it is**: `RequestSizeLimitMiddleware.dispatch` only acts `if request.headers.get(
  "content-length")`. A chunked-transfer request (no `Content-Length`) skips the check entirely and
  is streamed on to the handler. On a `ValueError` parsing the header it also silently passes
  (lines 49-50). No downstream body-size cap exists — file endpoints call `await file.read()` into
  memory unconditionally (`pdfs.py:27`, `notes.py:44`).
- **What it affects**: Memory-exhaustion / DoS on the shared worker via oversized uploads.
- **Trigger conditions**: One request with `Transfer-Encoding: chunked` and no `Content-Length`.
  No auth needed to reach the middleware; upload handlers require auth but the memory read happens
  before size is otherwise bounded.
- **Verified / Unverified**: Verified for the header logic. Whether the fronting platform (Render/
  Vercel) imposes its own body cap is environment-dependent and **unverified from the repo**.

### [MEDIUM] Overly broad CORS regex with credentials enabled
- **Location**: `backend/app/main.py:16-23`.
- **What it is**: `allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://
  localhost:\d+"` combined with `allow_credentials=True`, `allow_methods=["*"]`,
  `allow_headers=["*"]`. Any site hosted on any `*.vercel.app` or `*.onrender.com` subdomain (both
  are open public hosting platforms) is a permitted credentialed origin.
- **What it affects**: A malicious page on an attacker-controlled `*.vercel.app`/`*.onrender.com`
  origin can make credentialed cross-origin calls. Practical impact is bounded because auth is a
  Bearer token in the `Authorization` header (not an ambient cookie), so the attacker page cannot
  read a victim's token via CORS alone; the main exposure is any endpoint that behaves on ambient
  credentials and the general weakening of origin trust.
- **Trigger conditions**: Victim visits attacker page on a matching subdomain.
- **Verified / Unverified**: Verified config. Real-world impact depends on how the frontend stores
  the token (see the localStorage note under Coverage).

### [MEDIUM] Handwritten-note upload validates type by client header only (no magic bytes)
- **Location**: `backend/app/api/notes.py:37-45`.
- **What it is**: Type validation is `if file.content_type not in ALLOWED_TYPES` — the
  client-supplied `Content-Type`. The raw `file_bytes` are then uploaded to Supabase Storage
  (`notes.py:49-50`) and base64'd into the Gemini request. Contrast `pdfs.py:30` which checks actual
  magic bytes (`%PDF-`). No such content check exists here.
- **What it affects**: Arbitrary bytes can be stored in the `handwritten-notes` bucket under a path
  built from `current_user.id` and a server UUID (path is not attacker-controlled, so no traversal),
  and forwarded to the OCR API mislabeled.
- **Trigger conditions**: Authenticated user sets a whitelisted `Content-Type` on non-image bytes.
- **Verified / Unverified**: Verified.

### [MEDIUM] Vercel startup handler returns full traceback to the client
- **Location**: `api/index.py:26-40` (the `catch_all` handler's response includes
  `"traceback": startup_traceback`).
- **What it is**: On any import/startup failure of the real app, every route returns HTTP 500 with
  the exception string, a hint naming specific env-var names, and the **full Python traceback** in
  the JSON body.
- **What it affects**: Information disclosure — internal module paths, file layout, dependency/config
  details, and which secrets are expected — to any unauthenticated caller, but only while the
  Vercel deployment is in a failed-boot state.
- **Trigger conditions**: Vercel deploy target specifically; app fails to import (e.g. missing env
  var). Unauthenticated.
- **Verified / Unverified**: Verified in code. Whether it currently triggers depends on live env
  config (unverified).

### [MEDIUM] PDF-processing error text written into the `subject` column (schema misuse)
- **Location**: `backend/app/api/pdfs.py:94-99` (`process_pdf_background` failure path).
- **What it is**: On background processing failure, the code sets
  `"subject": f"ERROR: {error_str}"[:200]` — overwriting the document's subject field with a raw
  exception message. The `subject` column is meant to hold a user-facing classification and is
  displayed/used as such elsewhere (e.g. `subject` echoed to the UI on upload).
- **What it affects**: Data integrity (subject clobbered) and information disclosure — the raw
  backend exception string is persisted and later surfaced to the client via `GET /pdfs/list`
  (`pdfs.py:106-115`, `select("*")`).
- **Trigger conditions**: Any processing error on a user's own upload; the user then reads it back.
- **Verified / Unverified**: Verified.

### [MEDIUM] `verify_session_ownership` fails open when no `user_id` is recorded
- **Location**: `backend/app/services/teach/tools.py:21-31` (returns `True` at line 31).
- **What it is**: If a teaching session's state and plan both have a falsy `user_id`, the function
  returns `True` ("allow initialization"), granting access to any caller. All teach read/mutate
  routes rely on this (`teach.py:184,213,243,266`).
- **What it affects**: Access to a teaching session whose stored records lack a `user_id`.
- **Trigger conditions**: Existence of a session with no persisted `user_id` (depends on whether any
  code path creates state/plan without setting it — **partially unverified**, see Coverage).
- **Verified / Unverified**: The fail-open branch is verified; the reachability of an
  empty-`user_id` session was not fully traced.

### [MEDIUM] Quiz score integrity trusts client-computed correctness
- **Location**: `frontend/src/services/scoreTracker.ts:32-47` (`saveQuizScore`).
- **What it is**: The browser writes `quiz_scores` rows directly via the Supabase JS client, passing
  `is_correct` (and `topic`, `question_id`) as computed client-side. RLS on `quiz_scores`
  (`006_fix_missing_schema.sql:33-45`, `WITH CHECK (auth.uid() = user_id)`) constrains `user_id`
  only — it cannot validate that `is_correct` reflects a real correct answer.
- **What it affects**: A user can fabricate their own mastery/weak-topic analytics
  (`getWeakTopicAnalysis`, `scoreTracker.ts:51`).
- **Trigger conditions**: Authenticated user issuing a crafted insert against their own rows.
- **Verified / Unverified**: Verified for the write path.
- **If a quiz/assignment/grading feature goes live**: severity rises to High — any grade or
  entitlement derived from `quiz_scores` would be fully client-forgeable.

---

### [LOW] Signup returns the raw Supabase user object
- **Location**: `backend/app/api/auth.py:28` (`return {"message": ..., "user": res.user}`);
  also `/me` at `:40` (`return {"user": current_user}`).
- **What it is**: The endpoints serialize the full Supabase user object (including
  `app_metadata`, `user_metadata`, identities, timestamps, provider fields) rather than a curated
  DTO. `/login` at `:36` similarly returns the full `res.session` (access + refresh tokens — expected
  for login, but broad).
- **What it affects**: Exposure of internal auth object fields to the client. No secret beyond the
  tokens the client is entitled to; the concern is over-exposure/coupling.
- **Trigger conditions**: Normal signup/login.
- **Verified / Unverified**: Verified response shape.

### [LOW] Errors swallowed into HTTP 200 success responses
- **Location**: `backend/app/api/chat.py:24-31` (`/chat/ask` returns 200 with `model:"error"`);
  `chat.py:46-54` (`/v2/ask` returns 200 with `intent:"error"`);
  `backend/app/api/content_creator.py:24-30` (`/generate` returns 200 with `status:"failed"`).
- **What it is**: Broad `except Exception` blocks catch all failures (including RAG/LLM errors) and
  return a well-formed 200 body that embeds an error marker instead of a 4xx/5xx status.
- **What it affects**: Clients, monitoring, and retry logic cannot distinguish success from failure
  by status code; failures look like successes. (Note: `predict.py` and the file-upload handlers do
  raise proper `HTTPException`s, so this pattern is not repo-wide.)
- **Trigger conditions**: Any backend error inside these handlers.
- **Verified / Unverified**: Verified.

### [LOW] `print()` used for logging throughout; structured logger barely used
- **Location**: repo-wide — `grep` counts 107 `print(` vs 16 `logger.` calls under `backend/app/`.
  Examples that emit operational/user data to stdout: `vector_store.py:5,22,42,70`,
  `rag_service.py:132,165`, `notes.py:80,89`, `predict.py:100,123`, `pdfs.py:63,100`.
- **What it is**: The structured logger (`backend/app/core/logging.py`) is used in only a handful of
  places (`main.py`, `lesson_planner.py`); most modules `print()`. Several prints include exception
  strings and raw AI responses (`predict.py:123` prints `ai_response[:500]`), which land in
  hosting-platform stdout logs.
- **What it affects**: Inconsistent/unstructured logs; potential leakage of document-derived content
  and error internals into platform logs. No auth tokens or passwords were observed in print output.
- **Trigger conditions**: Normal operation.
- **Verified / Unverified**: Verified counts and sample lines; a full audit of every print's payload
  was not exhaustive.

### [LOW] Unpinned dependencies in both requirements files (no version floor)
- **Location**: `requirements.txt` (root) and `backend/requirements.txt` — both list packages with
  **no version constraints** (`fastapi`, `supabase`, `python-jose[cryptography]`, `passlib[bcrypt]`,
  `groq`, etc.).
- **What it is**: Nothing is pinned, so builds float to whatever is latest at deploy time. Known-CVE
  status cannot be asserted from the repo (no lockfile for Python). `python-jose` and `passlib` in
  particular have historically had advisories; presence of a vulnerable version cannot be confirmed
  or denied from an unpinned manifest.
- **What it affects**: Build reproducibility and CVE exposure are indeterminate.
- **Trigger conditions**: N/A (supply-chain/hygiene).
- **Verified / Unverified**: Unverified as an exploitable CVE — no resolved versions exist in-repo to
  check against advisories. Reported as a hygiene/uncertainty finding, not a confirmed vulnerable dep.

### [LOW] Deploy-target drift in CORS allow-list
- **Location**: `render.yaml:16-18` (`ALLOWED_ORIGINS` value) vs `backend/app/core/config.py:46`
  (default) vs commit `71b8868`.
- **What it is**: `config.py`'s default and commit `71b8868` add `https://aistudyassisant.onrender.com`
  to the origin list, but `render.yaml` hardcodes an `ALLOWED_ORIGINS` env value that omits it. The
  broad `allow_origin_regex` (see the CORS Medium finding) currently masks the discrepancy, so the
  drift is latent rather than functional today.
- **What it affects**: Origin allow-list differs by environment and by config source; a future
  regex tightening would surface the inconsistency.
- **Trigger conditions**: N/A (config drift).
- **Verified / Unverified**: Verified by comparing the two files. Root `requirements.txt` and
  `backend/requirements.txt` were compared and are currently **identical** (no drift there).

## Coverage Notes

- **RLS is present in the repo but structurally inert.** Policies exist in
  `backend/migrations/002-006`, but the backend authenticates to Supabase with the service-role key
  (`.env.example:5`, `supabase_client.py:5`), which bypasses RLS. This is why the two cross-tenant
  read findings are rated on the app-layer gap alone with no RLS backstop. Whether production
  actually sets a service-role key (vs an anon key) cannot be confirmed from the repo — but every
  write path (inserts on behalf of arbitrary `user_id`, storage writes) requires it, so anon key is
  implausible. **To close:** confirm the live `SUPABASE_KEY` role.
- **`document_chunks` table definition is not in version control.** No `CREATE TABLE document_chunks`
  exists under `backend/migrations/`; migrations only `ALTER` it (`006:11`). Whether it has a
  `user_id` column or its own RLS policy is unknown from the repo — the RPC
  `match_document_chunks` must JOIN `pdfs` to obtain `user_id` (`006:83-86`), which implies
  `document_chunks` has no direct `user_id`. **To close:** obtain the base schema for that table.
- **`pdfs`, `profiles`, `topic_decks`, `video_lessons`, `roadmap_stages` base schemas** are likewise
  only partially represented (migrations mostly `ALTER`/add). RLS on `pdfs` and `video_lessons` was
  not found as an explicit `CREATE POLICY` in-repo. Moot given service-role usage, but noted.
- **Empty-`user_id` teach session reachability** (Medium fail-open finding) was not fully traced
  through session-creation code; needs a walk of `get_learning_state`/`get_lesson_plan` writers.
- **Platform-level body-size / timeout caps** (Render, Vercel `maxDuration:300` in `vercel.json`,
  Railway) that might mitigate the Content-Length bypass are environment-side and not determinable
  from the repo.
- **Frontend token storage** (localStorage vs cookie) was not traced to a definitive conclusion,
  which bounds the practical impact rating of the CORS finding. `frontend/src/lib/supabase.ts` uses
  the default Supabase JS client (localStorage session persistence by default), but this was not
  confirmed against the app's session handling.
- **Dependency CVEs** cannot be asserted — both `requirements.txt` files are unpinned and there is
  no Python lockfile; `frontend/package.json` pinned versions were not cross-checked against live
  advisory databases in this pass.
- **No shell/`ffmpeg`/`subprocess`/`os.system` invocation exists** anywhere in `backend/` (repo-wide
  grep returned zero matches), so the anticipated shell-injection surface in the video compositor is
  **not present**; video work uses in-process Python libraries.
- **Heavy synchronous work on shared workers** (PDF extraction/embeddings in `pdfs.py:73-103` via
  FastAPI `BackgroundTasks`, PPT/video generation) runs in-process on a 2-worker Render deployment
  (`render.yaml:9`); this is a real resource-starvation surface but was assessed as a design
  characteristic rather than a discrete exploit and is folded into the Content-Length DoS note.

## Explicitly Out of Scope

- **Billing system** — `backend/app/api/billing.py`, `frontend/src/services/billing.ts`,
  PricingPage, PaymentVerifyPage, and Cashfree integration — excluded per project owner; not yet in
  production use. Note that the [HIGH] plan-enforcement finding and the [MEDIUM] quiz-integrity
  finding both call out how their severity changes **if** billing/graded features go live against
  this code as-is; those forward-looking notes are included because the enforcement gap exists today
  regardless of whether the paid feature is switched on.
