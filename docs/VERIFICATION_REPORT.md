# Sospana Sonke — Accuracy & Efficiency Verification

**Date:** 11 August 2026 · **Scope:** full Phase 1 (MVP) — backend + Next.js frontend

This report records the checks run across the whole platform after the frontend was
completed, covering correctness (accuracy) and performance (efficiency).

---

## 1. Backend — automated tests

**Result: 112 / 112 passing.** The suite covers every module and, importantly, the
*rules* that make the product trustworthy, not just happy paths:

- **Auth & access control** — register/verify/login/refresh, JWT, RBAC; a user can only ever reach their own records (ownership-isolation tests across profile, CV, matches, applications, documents, reports).
- **Company database & URL tester** — CSV import with de-dup, admin gating, URL heuristic + HTTP + error paths.
- **Scraper** — Greenhouse/Lever/SmartRecruiters/JSON-LD parsers against saved samples, content-hash dedup, change-detection (closing stale roles), robots-disallowed and HTTP-error handling.
- **Matching** — deterministic scoring, hard-requirement gate, weight configurability, band thresholds, pre-filter exclusions, confidence.
- **Documents** — truthfulness validator **catches fabrication** (unsupported skill, unknown employer, inflated years), ATS scoring, PDF/DOCX generation.
- **Applications** — full lifecycle + audit trail, anti-spam caps, duplicate/min-score/do-not-apply gates, `UNKNOWN` answer flagging.
- **Subscriptions** — state machine, access gating (402), payment idempotency, webhook signature verification (Paystack HMAC + mock).
- **Dashboards/reports & notifications/scheduler** — aggregates, MRR, report PDF, idempotent notifications, job runner.

## 2. Backend — end-to-end journey (live, in-process)

A single run drove the **real API** through the whole candidate loop against a seeded
vacancy. **14 / 14 checks passed:**

register + login → profile built → subscription ACTIVE @ R100 → matching ran (≥1 matched)
→ match decision **APPLY** with reasons + sub-scores → tailored CV **truthful** + ATS > 0
→ application **AWAITING_APPROVAL** → **unknown answers flagged** (never-fabricate) →
approve → **SUBMITTED** → dashboard reflects activity → report generated → **strong-match
notification** created → **gating returns 402** for a user without an active subscription.

## 3. Frontend — build & type-check

**Result: clean production build, 15 routes, types valid** (`next build`). App Router +
TypeScript (strict) + Tailwind. Pages: login, register, dashboard, profile, cv, matches,
matches/[id], applications, applications/[id], subscription, notifications, admin,
admin/companies. Bundle ~87 kB shared JS; per-route 2.5–4.5 kB. The typed API client
centralises auth and error handling; paid-feature 402s surface as a subscribe prompt.

## 4. Efficiency review

**Design-level efficiency (the cost model's foundation) is in place:**

- **Shared vacancy work** — scraping/extraction is done once per vacancy for the whole platform (a `vacancies` table keyed by content hash), never per candidate.
- **Deterministic pre-filter before scoring** — excluded companies/roles and salary floor discard vacancies with zero AI/scoring cost; only survivors are scored.
- **Deterministic scoring** — matching, truthfulness, ATS, and requirement classification are pure Python (no LLM in the hot path), so they are fast, free, and cache-free by nature.
- **Sector/company caching** inside a matching run; **content-hash dedup** so re-scans don't reprocess unchanged vacancies.
- **Indexes** on every foreign key and on lookup/dedup columns (email, jse_code, content_hash, status, related_id).
- **Background-ready** — scans and matching are exposed as jobs runnable off the request path via the scheduler CLI.

**One N+1 found and fixed:** the candidate `GET /matches` list built each row with two
per-row `db.get` calls (vacancy + company). Refactored to **batch-load** all vacancies
and companies for the page in two queries. Verified green afterwards.

**Remaining per-item queries judged acceptable (small, bounded, indexed), with the
future optimisation noted:**

| Location | Pattern | Why acceptable now | Future |
|---|---|---|---|
| `scan_service` dedup | 1 indexed lookup per scraped vacancy | Bounded by a single source's postings; indexed on `content_hash` | Batch by hash set if a source returns thousands |
| `match_service` requirements | 1 query per candidate vacancy for its requirements | Runs off-request; pre-filter shrinks the set first | Eager-load requirements with the vacancy |
| `report_service` top/rejected | `db.get` for ≤10 rows | Tiny fixed bound | — |

## 5. Accuracy guarantees confirmed

- **No fabrication** — the truthfulness validator runs on every generated CV and is proven by test to reject unsupported skills/employers/qualifications and inflated experience; application answers not in the profile are returned as `UNKNOWN — CANDIDATE INPUT REQUIRED`.
- **Candidate control** — nothing is submitted without candidate action; approval/assisted/automatic modes; do-not-apply matches cannot be turned into applications.
- **Money & permissions are deterministic** — scoring, gating, caps, and subscription state are code, never an LLM.
- **Explainability** — every match stores reasons, gaps, sub-scores, confidence, band, and engine version.

## 6. Known limitations / recommended next steps (not blockers)

- **Alembic migrations** should replace the `create_all` bootstrap before production (Step 0.5).
- **Background workers** (RQ/Celery) + a real scheduler (APScheduler/cron) should drive the jobs in production; the functions and CLI are ready.
- **PDF vacancy pages** and **JavaScript-rendered ATS portals** (Playwright) are Phase 2, as is **automated submission** (per-source policy).
- Email/SMS/push beyond dashboard + SMTP, and MFA/social login, are Phase 2.

**Overall:** the Phase 1 MVP is functionally complete and internally consistent — 112 unit/integration tests and 14 end-to-end checks pass, the frontend builds cleanly, the one real N+1 was fixed, and the truthfulness/gating/candidate-control guarantees are verified by test.
