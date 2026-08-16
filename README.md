# Sospana Sonke

**AI-powered job discovery, CV tailoring and application platform for South Africa.**
*"We find the opportunities. We tailor your application. We help you apply smarter."*

This repository contains the **Phase 1 foundation** of the platform described in the
[Product & Technical Blueprint](docs/). It is a real, running, tested codebase — not a mockup.

## What works today (Phase 1 foundation)

- **Authentication** — register, email verification, login, token refresh, `/me`, with Argon2 password hashing and JWT tokens.
- **Role-based access control** — candidate vs administrator.
- **Company database** — the JSE + State-Owned-Entity seed data (367 companies), with CSV import (admin-only) and de-duplication.
- **Careers-URL tester** — validates that a stored careers URL resolves and looks like a careers page, and updates each company's status (this is how *all* links get verified at scale).
- **Candidate profile** — full profile plus education, certifications, work experience, and skills, each ownership-scoped, with a `confirmed_by_candidate` flag separating verified fact from AI suggestion.
- **CV upload & intelligence** — upload PDF/DOCX/TXT (size, type, magic-byte and malware-scan checks), the original is stored immutably, text is extracted, and an AI provider produces a structured suggestion you can import into your profile as *unconfirmed* data.
- **AI provider abstraction** — swappable providers (a free offline heuristic by default, a Claude implementation when configured); it never fabricates candidate facts.
- **Vacancy discovery engine** — a strategy framework that reads vacancies from Greenhouse, Lever, and SmartRecruiters JSON feeds and from schema.org JobPosting data on static pages; respects robots.txt with rate limiting and backoff; normalises and de-duplicates vacancies by content hash; classifies each requirement as hard vs soft; detects closed roles; and exposes admin scan + vacancy-browsing endpoints.
- **Matching engine** — a cheap deterministic pre-filter followed by a configurable weighted scorer across eight dimensions, a hard-requirement gate, and an explainable APPLY / REVIEW / DO-NOT-APPLY decision with plain-language reasons and gaps, a confidence level, and a match band. Scoring is deterministic (never LLM-controlled); weights and thresholds are admin-editable.
- **Document generation** — from a match, generates a truthful tailored CV (PDF + DOCX) built only from confirmed profile data, with vacancy-relevant skills/experience floated to the top, plus a cover letter. Every document passes a **truthfulness validator** that rejects any skill, employer, qualification, or inflated experience figure not backed by the profile, and each CV gets an **ATS compatibility score** with a breakdown.
- **Applications & tracking** — prepares an application from a match through the full status lifecycle with an **immutable audit trail**; three modes (automatic / approval / assisted); **anti-spam caps** (per-day, per-week, minimum score, duplicate prevention, do-not-apply gate); and **never-fabricated answers** — factual questions come from the profile, and anything absent is flagged `UNKNOWN — CANDIDATE INPUT REQUIRED` for the candidate to fill. Candidate preferences (mode, caps, exclusions) also feed the matcher.
- **Subscription & payments** — the R100/month subscription behind a **swappable payment provider** (Paystack for production with HMAC-SHA512 webhook verification; a Mock provider for offline dev/tests). A subscription **state machine** (TRIAL → ACTIVE → PAST_DUE → CANCELLED/EXPIRED) with a grace window, **access gating** that returns 402 on matching / document / application endpoints when inactive, checkout, cancel, and **idempotent** webhook handling.
- **Dashboards & reports** — a candidate dashboard (vacancies found, strong matches, CVs, applications, awaiting-action, interviews, offers, subscription) and an admin/business dashboard (registered candidates, active + paying subscriptions, estimated MRR, company/source health, vacancy and application counts), plus a per-cycle **candidate intelligence report** rendered to a downloadable PDF.
- **Scheduler & notifications** — a swappable email provider (console default, SMTP for production), idempotent dashboard notifications (and optional email) for strong matches, action-required applications, and ready reports, plus recurring jobs (scan-all-companies, match-all-candidates) with a run log and an admin-configurable cron schedule (run via `python -m scripts.run_scheduled_job <job>`).
- **Automated tests** — 112 tests covering auth, access control, CSV import/dedup, URL tester, profile CRUD + ownership isolation, the CV pipeline, the scraper, the matching engine, document generation, the application lifecycle, subscriptions, dashboards/reports, and notifications/scheduler.

**Phase 1 (MVP) is complete** — all 16 MVP modules plus the Next.js frontend, built, tested, and verified end-to-end.

**Phase 2 in progress** — the first Phase 2 module, **safe automated application submission** (Playwright, per-source policy, never bypassing CAPTCHA/login/MFA), is built and tested, including a live headless-browser submission test. See `docs/PHASE2_STATUS.md`.

See [`docs/PHASE1_STATUS.md`](docs/PHASE1_STATUS.md) for exactly what is built and what comes next.

## Repository layout

```
sospana-sonke/
├── backend/            # FastAPI application (this is what runs today)
│   ├── app/            #   config, security, db, models, schemas, api, services
│   ├── scripts/        #   seed importer / admin creator
│   ├── seed/           #   company_database_import.csv (367 companies)
│   ├── tests/          #   pytest suite
│   └── requirements.txt
├── frontend/           # Next.js app (scaffold placeholder — built in the next module)
├── docs/               # Blueprint, legal pack, link report, phase-1 status
├── docker-compose.yml  # Postgres + backend for a one-command local run
└── README.md
```

## Run the backend locally (no Docker, uses SQLite)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# seed the 367 companies and create an admin login
python -m scripts.import_companies --admin admin@sospanasonke.co.za 'ChangeThisPassword1!'

# run the API
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs for the interactive API
```

## Run the tests

```bash
cd backend && source .venv/bin/activate
pytest
```

## Run with Docker (Postgres)

```bash
cp backend/.env.example backend/.env      # then edit SECRET_KEY etc.
docker compose up --build
```

## Security & privacy

Passwords are Argon2-hashed; secrets come from environment variables (never committed);
the platform is designed to POPIA requirements. Before processing real users' data,
finalise the documents in [`docs/Sospana_Sonke_Legal_Pack.md`](docs/Sospana_Sonke_Legal_Pack.md)
with a South African attorney.
