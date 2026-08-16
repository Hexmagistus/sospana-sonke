# Phase 1 — Build Status

Phase 1 (the MVP) is being built **one module at a time**, each fully working and tested before the next, per the blueprint's development method. This file tracks progress.

## ✅ Built and tested in this iteration

| Blueprint step | Module | Status |
|---|---|---|
| Step 0 | Project scaffold, config, Docker, DB engine/session, test harness | ✅ Done |
| Step 1 | **Authentication** — register, verify email, login, refresh, `/me`; Argon2 hashing; JWT; RBAC (candidate/admin) | ✅ Done, tested |
| Step 4 | **Company database** — model, admin CSV import with de-dup, listing with filters; seeded with 367 companies | ✅ Done, tested |
| URL tester | **Careers-URL tester** — resolves + heuristically classifies careers pages, updates status | ✅ Done, tested |
| Step 2 | **Candidate profile** — profile + education/certifications/experience/skills CRUD, ownership-scoped, `confirmed_by_candidate` flags | ✅ Done, tested |
| Step 3 | **CV upload & intelligence** — PDF/DOCX/TXT upload, size/type/magic-byte + malware-scan hook, immutable original in object storage, text extraction, AI structuring, apply-to-profile as unconfirmed data | ✅ Done, tested |
| — | **AI provider abstraction** — pluggable providers (heuristic default, Claude implementation), never fabricates | ✅ Done, tested |
| Step 5 | **Scraper & vacancy extraction** — strategy framework (Greenhouse/Lever/SmartRecruiters JSON feeds + static JSON-LD), robots.txt + rate limiting + backoff, normalisation, content-hash dedup, hard/soft requirement classification, change detection, admin scan + vacancy routes | ✅ Done, tested |
| Step 6 | **Matching engine** — cheap deterministic pre-filter, configurable weighted sub-scores (8 dimensions), hard-requirement gate, explainable APPLY/REVIEW/DO_NOT_APPLY decision with reasons + gaps, confidence + band; per-candidate match run/list/detail; admin-editable weights & thresholds | ✅ Done, tested |
| Step 7 | **Document generation** — truthful tailored CV (PDF + DOCX) built from confirmed profile data with vacancy-relevant reordering; truthfulness validator (rejects any unsupported claim/inflated years); ATS compatibility scorer; cover-letter generator; generate/list/download routes | ✅ Done, tested |
| Step 8 | **Applications & tracking** — application settings (mode, caps, min score, exclusions); prepare-from-match with anti-spam caps, duplicate + min-score + do-not-apply gating; three modes; never-fabricate answers (UNKNOWN flagging); full status lifecycle with an immutable audit trail; approve / mark-submitted / status / fill-answer routes; exclusions feed the matcher | ✅ Done, tested |
| Step 9 | **Subscription & payments** — Subscription + Payment models; swappable payment provider (Paystack with HMAC-SHA512 webhook verification + Mock for dev); state machine (TRIAL→ACTIVE→PAST_DUE→CANCELLED/EXPIRED) with grace; access gating (402) on matching/documents/applications; checkout, cancel, idempotent webhooks | ✅ Done, tested |
| Step 10 | **Dashboards & reports** — candidate dashboard aggregates (vacancies, matches, CVs, applications, interviews/offers, subscription); admin/business dashboard (users, active + paying subs, estimated MRR, company/source health, vacancy & application counts); per-cycle candidate intelligence report rendered to downloadable PDF | ✅ Done, tested |
| Step 11 | **Scheduler & notifications** — email provider abstraction (console default, SMTP for prod); idempotent dashboard notifications (+ optional email) for strong matches, action-required, and report-ready, wired into matching/applications/reports; recurring jobs (scan-all, match-all-candidates) with a JobRun log and admin-configurable cron schedule; CLI + admin trigger | ✅ Done, tested |

**🎉 Phase 1 (MVP) backend is complete — all 16 MVP modules from the blueprint are built and tested (112 tests passing).**

**Tests:** 112 passing (adds strong-match/action-required/report-ready notifications, idempotency, mark-read, admin schedule get/update, job trigger + run log, and unknown-job handling).

## ✅ Frontend (Next.js) — built & building clean

A full candidate + admin web app (App Router, TypeScript, Tailwind) wired to the API: login/register, dashboard, profile (+skills/education), CV upload → import, matches + explainable detail (generate CV/cover letter, prepare application), applications (lifecycle + answers + audit trail), subscription, notifications, admin dashboard, and company database (CSV import + scan). `next build` passes with 15 routes and valid types. See `frontend/`.

**Full verification pass:** 112 backend tests pass, a 14/14 end-to-end journey through the live API passes, the frontend builds clean, and one N+1 in `GET /matches` was found and fixed. Details in `docs/VERIFICATION_REPORT.md`.

## ▶️ Remaining work

| Item | Notes |
|---|---|
| Step 0.5 | Alembic migrations to replace the `create_all` bootstrap before production. |
| Production scheduler | Point cron / APScheduler / Celery beat at `python -m scripts.run_scheduled_job <job>` using the intervals from `GET /admin/schedule`. |
| Phase 2 | Automated submission (Playwright, per-source policy), JavaScript-ATS coverage, SMS/push, MFA, interview prep. |

**Config note:** payments default to `PAYMENT_PROVIDER=mock` and a 14-day trial (`TRIAL_DAYS`); email defaults to `EMAIL_PROVIDER=console` with `NOTIFY_EMAILS=false`, so the app runs and tests pass offline. For production set `PAYMENT_PROVIDER=paystack` + `PAYSTACK_SECRET_KEY` (webhook → `/api/v1/subscription/webhook`) and `EMAIL_PROVIDER=smtp` + SMTP creds with `NOTIFY_EMAILS=true`.
| Step 9 | Subscription & payments | Paystack behind a payment abstraction; state machine; webhooks. |
| Step 10 | Dashboards & reports | Candidate + admin dashboards; PDF reports. |
| Step 11 | Scheduler & notifications | Recurring jobs; email + dashboard alerts. |
| Step 12 | Hardening & launch | Security review, legal integration, cost tuning, E2E, backup drill. |
| — | **Frontend** (Next.js) | Currently a placeholder; built alongside the backend modules above. |

## Design rules being honoured

- Money, permissions, and scoring are deterministic backend code — never the AI.
- The AI never fabricates candidate facts; missing data is marked for candidate input.
- Nothing is submitted to an employer without candidate authorisation.
- Careers links are verified by the system, not trusted from the seed data.
