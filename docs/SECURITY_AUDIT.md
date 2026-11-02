# LearnByGenie — Application Security & Threat Model Audit

**Audit Date:** November 2026  
**Auditor:** Application Security Engineer & Principal Architect  
**Classification:** Confidential — Engineering Security Baseline  

---

## 1. Executive Summary

A comprehensive application security audit was performed covering authentication, authorization, multi-tenant isolation, cryptographic integrity, API security, and client-side secret leakage across LearnByGenie.

Overall, foundational security middleware (CORS origin restrictions, SlowAPI rate limiting, security headers middleware, and request body size limits) is operational in `backend/app/main.py`. Previous critical findings (unauthenticated agent routes, IDORs on video lessons) have been remediated in code. However, several critical architectural security gaps remain:
1. **Unenforced Multi-Tenant Role Isolation:** Backend lacks fine-grained role dependencies for `parent`, `teacher`, `school_admin`, and `content_creator`.
2. **Supabase Paused / DNS Outage Vulnerability:** Dependency on an external unresolvable cloud domain can lock out authorized users or trigger unhandled 503 errors.
3. **Absence of Parent-Student Verification Guards:** Without cryptographically verified linkage, parental portals risk severe cross-tenant data exposure.

---

## 2. Review of Historical Findings (From 2026-08-31 Audit)

| Finding ID | Severity | Description | Current Status | Verification Details |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | **CRITICAL** | Five agent endpoints had no authentication (`/orchestrator/route`, `/librarian/retrieve`, `/tutor/turn`, `/content-creator/generate`, `/content-creator/status/{id}`) | **FIXED** | All five endpoints now declare `current_user = Depends(get_current_user)`. Ownership checks enforced on job status polling. |
| **SEC-02** | **HIGH** | Cross-tenant document read via Exam Predictor (`get_top_chunks` had no user filter) | **FIXED** | RPC rewritten and caller scopes `user_id = current_user.id`. |
| **SEC-03** | **HIGH** | Cross-tenant document read via chat global modes (`get_all_chunks` dropped `user_id`) | **FIXED** | Scoped strictly to `current_user.id` across all chat and RAG pipelines. |
| **SEC-04** | **HIGH** | IDOR on video lessons via in-memory `PROJECT_STORE` | **FIXED** | Store lookups verify lesson ownership before serving or modifying records. |
| **SEC-05** | **HIGH** | Backend runs under Supabase service-role key, bypassing PostgreSQL RLS | **PARTIALLY MITIGATED** | Application-layer scoping (`.eq("user_id", current_user.id)`) added to all routes. However, DB-level RLS still bypassed when using service key; local fail-closed validation enforced. |

---

## 3. Threat Modeling & Newly Identified Vulnerabilities

### SEC-06 [HIGH] Missing Server-Side Role-Based Authorization Guards
- **Location:** `backend/app/core/dependencies.py`
- **Vulnerability:** The backend only exports `get_current_user` and `get_current_admin_user`. There are no dedicated role guards for `require_teacher`, `require_parent`, `require_school_admin`, or `require_content_creator`.
- **Risk:** Any authenticated student can call teacher endpoints (e.g. creating live quizzes or modifying classroom curriculums) or parent endpoints (viewing other students' progress).
- **Remediation:** Implement a flexible, parameterized dependency `require_role(allowed_roles: List[str])` and attach it to institutional endpoints.

### SEC-07 [HIGH] Unverified Parent-to-Student Linkage (IDOR Risk)
- **Location:** Institutional Portals (Target Design)
- **Vulnerability:** If parent accounts can link to students by merely providing a student ID without an out-of-band verification token (invite code or school confirmation), an attacker can link to any student and read their sensitive diagnostic scores and mistake patterns.
- **Remediation:** Implement an invitation/code verification handshake in `parent_student_links` with cryptographic token validation before granting read permissions.

### SEC-08 [MEDIUM] Unhandled DNS / Cloud Database Outage Handling
- **Location:** `backend/app/db/supabase_client.py`, `backend/app/core/dependencies.py`
- **Vulnerability:** When the remote Supabase endpoint is paused or unresolvable (`[Errno 11001] getaddrinfo failed`), `supabase.auth.get_user(token)` crashes with 401 and database writes crash with 503, rendering the platform completely unusable even for local testing and offline operation.
- **Remediation:** Implement local JWT secret decoding via `pyjwt` using `SUPABASE_JWT_SECRET` so authentication does not require external network roundtrips, and provide a persistent local database/memory fallback for offline resilience.

### SEC-09 [LOW] Sensitive Client-Side Environment Variables Check
- **Location:** `frontend/.env*`, `frontend/src/`
- **Audit Findings:** Client bundle inspected. No secret keys (`SUPABASE_KEY` service role, `GEMINI_API_KEY`, `GROQ_API_KEY`) are present in client code. Only public publishable keys (`VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`) are referenced.
- **Status:** **PASS (Secure)**.

---

## 4. Security Hardening Specifications

1. **Role-Based Permission Dependency:**
   ```python
   def require_role(allowed_roles: List[str]):
       def role_checker(current_user = Depends(get_current_user)):
           user_role = getattr(current_user, "role", None) or \
                       current_user.app_metadata.get("role") or \
                       current_user.user_metadata.get("role") or "student"
           if user_role not in allowed_roles and "super_admin" not in user_role:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail=f"Access denied. Requires one of roles: {allowed_roles}"
               )
           return current_user
       return role_checker
   ```

2. **Local Cryptographic JWT Verification (Network-Resilient):**
   ```python
   import jwt
   def verify_token_locally(token: str, secret: str) -> dict:
       try:
           payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
           return payload
       except Exception as e:
           raise HTTPException(status_code=401, detail="Invalid token signature")
   ```

3. **CORS & Domain Whitelisting:**
   - Active origins strictly bounded to:
     - `http://localhost:5173`, `http://localhost:5174`, `http://localhost:8000`
     - `https://learnbygenie.online`, `https://www.learnbygenie.online`
     - `https://learnbygenie.onrender.com`, `https://aistudyassisant-inky.vercel.app`
   - Wildcards rejected in production.

