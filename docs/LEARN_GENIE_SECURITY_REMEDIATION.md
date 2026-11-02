# LEARN GENIE — APPLICATION SECURITY & TENANT ISOLATION REMEDIATION REPORT

**Version:** 2.0.0  
**Classification:** Confidential Engineering Security Baseline  
**Auditor Roles:** Application Security Engineer, Principal Distributed Systems Architect  
**Codebase:** LearnByGenie (`backend/app/core/dependencies.py`, `backend/app/api/portals.py`, `backend/app/services/portals/`)  
**Audit Standard:** OWASP Top 10 (2021/2026), India Digital Personal Data Protection Act (DPDP), 2023.

---

## 1. Executive Summary

In accordance with Section 11 and Section 16 of the Learn Genie Master Execution Plan, a rigorous forensic audit and code remediation of the authentication, authorization, cryptographic integrity, and multi-tenant persistence layers was executed.

All identified critical and high vulnerabilities—specifically production mock token exposure, unverified signature decoding bypasses, hardcoded parental child linkage, and missing role guards—have been systematically eliminated in code with passing test verification.

---

## 2. Remediated Vulnerabilities & Forensic Evidence

### SEC-01 [CRITICAL]: Production Mock Token Exposure & Bypass
- **Vulnerability Description:** Previously, `backend/app/core/dependencies.py` checked `if token in MOCK_DEV_USERS:` without validating the runtime environment. In a production deployment, any user submitting `Authorization: Bearer dev-admin-token` or `dev-super-admin-token` received immediate unauthenticated `super_admin` access.
- **Root Cause:** Environment gating was missing from the token resolution sequence.
- **Remediation Implemented:**
  - Added `_is_dev_environment() -> bool` which strictly enforces that mock tokens are only evaluated if:
    ```python
    env = (getattr(settings, "ENVIRONMENT", "") or os.environ.get("ENVIRONMENT", "development")).lower()
    return env in ("development", "test", "local") and env != "production"
    ```
  - In `production`, any mock token immediately bypasses dev evaluation and is submitted to cryptographic verification, which fails and returns HTTP 401 Unauthorized.
- **Verification Evidence:** `test_institutional_portals_and_gamification.py` and `test_production_smoke_feature4.py` verify that credentials without valid signatures fail closed.

### SEC-02 [CRITICAL]: Unverified JWT Signature Fallback (Token Forgery)
- **Vulnerability Description:** Previously, `dependencies.py` contained a fallback decoding block:
  ```python
  payload = jwt.decode(token, options={"verify_signature": False})
  ```
  This allowed an attacker to construct an arbitrary unsigned JWT payload containing any `sub` (user ID) and any `role` (e.g. `super_admin`), completely bypassing cryptographic authentication whenever cloud Supabase Auth was unreachable.
- **Remediation Implemented:**
  - The unverified decode block was **completely deleted** from the codebase.
  - Authentication now strictly requires cryptographic signature validation:
    1. Remote Supabase Auth validation via `supabase.auth.get_user(token)`, OR
    2. Local HS256 cryptographic verification using `SUPABASE_JWT_SECRET` with `verify_signature: True` and `verify_exp: True`.
  - Roles extracted from claims are validated against `VALID_SYSTEM_ROLES = {"student", "parent", "teacher", "school_admin", "content_creator", "admin", "super_admin"}`. Arbitrary client claims are discarded and default safely to `"student"`.
  - If cryptographic verification fails, the endpoint fails closed with HTTP 401 Unauthorized.

### SEC-03 [HIGH]: Hardcoded Parent-Child Linkage (IDOR Risk)
- **Vulnerability Description:** Previously, `backend/app/api/portals.py` hardcoded `student_id = "a56da972-0f19-418d-b0f7-de91ff114190"` in the `POST /api/portals/parent/link-child` endpoint, and `PortalsRepository` automatically linked any parent with ID `...0077` to that student.
- **Remediation Implemented:**
  - Implemented authentic student invite code generation (`POST /api/portals/student/generate-parent-code`) generating secure codes (e.g. `GENIE-XXXXXX`).
  - `PortalsRepository.link_parent_with_code` validates the invitation code against the active code vault before creating a verified `parent_student_link`.
  - In production, unverified or unrecognized codes raise HTTP 400 Bad Request with `"Invalid, expired, or unrecognized student invitation code."`
  - Replaced hardcoded default student ID with dynamic verified linking.
- **Verification Evidence:** `test_parent_student_invite_code_handshake` in `test_institutional_portals_and_gamification.py` passes.

### SEC-04 [HIGH]: Server-Side Multi-Tenant Role-Based Access Control (RBAC)
- **Vulnerability Description:** Earlier versions of the platform lacked role enforcement dependencies, allowing students to access teacher and parent endpoints.
- **Remediation Implemented:**
  - Created parameterized dependency `require_role(allowed_roles: List[str])` in `backend/app/core/dependencies.py`.
  - Defined explicit role guards:
    - `require_student`: Restricted to `student`, `admin`, `super_admin`.
    - `require_parent`: Restricted to `parent`, `admin`, `super_admin`.
    - `require_teacher`: Restricted to `teacher`, `admin`, `super_admin`.
    - `require_school_admin`: Restricted to `school_admin`, `admin`, `super_admin`.
    - `require_content_creator`: Restricted to `content_creator`, `admin`, `super_admin`.
    - `require_admin`: Strictly restricted to `admin`, `super_admin`.
  - Bound these guards across all portal endpoints in `backend/app/api/portals.py`.
- **Verification Evidence:** `test_parent_portal_blocks_unauthorized_student` verifies that student role calling parent endpoints is rejected with HTTP 403 Forbidden.

### SEC-05 [MEDIUM]: Gamification XP Replay & Client Manipulation
- **Vulnerability Description:** If clients could submit arbitrary XP amounts or replay reward triggers, students could artificially inflate levels and streaks.
- **Remediation Implemented:**
  - Server-Authoritative Two-Ledger Architecture: XP Ledger (Ledger A) is completely isolated from Academic Mastery Evidence (Ledger B).
  - XP amounts are derived from canonical blueprint values (`CANONICAL_BLUEPRINT_XP_AMOUNTS`), not client-supplied values.
  - Idempotency keys (`idempotency_key` column with UNIQUE constraint in `xp_ledger`) prevent replay attacks: replayed requests return the existing transaction without incrementing XP.
  - Daily cap of 10 XP/day enforced server-side for repeated easy practice items (`REPEATED_EASY_PRACTICE`).

---

## 3. India DPDP Act, 2023 Child Safety Compliance Register

| DPDP Requirement | Platform Implementation | Verification Status | Legal Review Action |
| :--- | :--- | :--- | :--- |
| **Section 9(1): Verifiable Parental Consent** | Child accounts can only be viewed by parents after reciprocal invitation handshake (`parent_student_links.verification_status = 'verified'`). | **ACTIVE IN CODE** | Legal counsel to review consent declaration notice copy. |
| **Section 9(2): Ban on Behavioral Tracking of Children** | No third-party ad tracking, no profiling for advertising, no marketing SDKs. Telemetry is strictly pedagogical. | **PASS (Clean)** | Zero advertising scripts present in frontend bundle. |
| **Section 6(1): Purpose Limitation** | Diagnostic responses and mistake patterns are processed solely for personal mastery recommendations and teacher instruction. | **PASS** | Formalized in `docs/LEARN_GENIE_LEARNING_ENGINE_SPEC.md`. |
| **Section 8(7): Data Retention & Erasure** | Super Admin portal has user management capabilities; deletion hooks purge student profiles and evidence cascades. | **PARTIALLY WORKING** | Implement one-click GDPR/DPDP data export & purge pipeline. |
| **Class-Level Leaderboard Safety** | Classes 6–8 have public individual leaderboards disabled; cooperative goals only. Pseudonymized weekly leagues for Classes 9–12. | **ACTIVE IN SCHEMA** | Enforced by student grade check in gamification service. |

---

## 4. Production Security Invariants

1. **Fail-Closed Principle:** In the event of network disruption to Supabase Auth, any JWT that cannot be verified using `SUPABASE_JWT_SECRET` HS256 cryptographic signature is rejected.
2. **Authoritative Backend Authority:** Client applications never write directly to mastery states, difficulty ratings, or XP ledgers.
3. **Audit Trails:** Privileged role promotions and security events are logged with UTC timestamps and user attribution.
