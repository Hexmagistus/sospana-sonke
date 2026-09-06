# Sospana Sonke — Security Hardening Report

**Date:** 6 September 2026
**Scope:** Backend (FastAPI / Render / Postgres) and frontend (Next.js / Vercel)
**Prepared by:** Claude (Opus)

> **Framing, up front and honestly:** this pass *reduces risk* — it does not make
> the system "unhackable," and no report should ever claim that. It closes the
> specific weaknesses found in the audit, documents what is still open, and gives a
> relative before/after read so you can see the movement. Everything below is about
> raising the cost and narrowing the surface for an attacker, not eliminating risk.

---

## A. What changed this pass

Seven issues were identified in the read-only audit; all seven are now addressed and
committed locally (not pushed — you push).

| # | Fix | Where | Commit |
|---|-----|-------|--------|
| 1 | Refuse to boot in production if `SECRET_KEY` is still the placeholder | `backend/app/core/config.py` | `62a8b9a` |
| 2 | Mask email-verification / password-reset tokens in production API responses | `backend/app/schemas/auth.py`, `routes_auth.py` | `62a8b9a` |
| 3 | Per-route rate limiting on all auth endpoints (login, register, google, refresh, MFA, password-reset) | `backend/app/core/rate_limit.py`, `routes_auth.py` | `62a8b9a` |
| 4 | Disable `/docs`, `/redoc`, `/openapi.json` in production | `backend/app/main.py` | `62a8b9a` |
| 5 | Content-Security-Policy on the web app, shipped **Report-Only** | `frontend/next.config.mjs` | `4df5a5b` |
| 6 | Lower the public vacancy-list cap from 5000 → 200 per page (anti-bulk-scrape) | `backend/app/api/routes_vacancies.py` | `8cf8dfa` |
| 7 | Copy-deterrence layer (UX only) | `frontend/src/components/CopyGuard.tsx`, `layout.tsx` | `4df5a5b` |

A strict CSP (`default-src 'none'`) was also added to the JSON API responses, and a
Postgres/ORM-only, admin-verified baseline (below) was confirmed already in place.

## B. Secrets & credentials (type + location only — no values disclosed)

- **`SECRET_KEY`** — injected in production by Render (`generateValue: true`). The
  weak in-code placeholder now triggers a hard startup failure if it is ever used
  with `ENV=production`.
- **`DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CORS_ORIGINS`** — Render
  dashboard environment variables (`sync: false`), not stored in the repo.
- **`.env` / `*.db`** — excluded by `.gitignore`; a stray test-DB journal was also
  added to the ignore list this pass.
- No hardcoded live secrets were found in tracked files. (Values were never read
  out or recorded — only their type and location.)

## C. Existing strengths (confirmed safe — no change needed)

The audit confirmed several things were already done correctly and left them alone:
admin role is always re-verified from a fresh server-side DB fetch (never trusted
from the JWT/client); ownership/IDOR checks are consistent across resource routes;
the codebase is ORM-only with no raw SQL; CORS is a real allowlist (no
wildcard-with-credentials); the cron endpoint uses `hmac.compare_digest` and returns
404 when unconfigured; path traversal is defended in `services/storage.py`; and the
matching-algorithm weights are admin-only. Passwords are hashed with Argon2.

## D. Remaining risks & limitations (read this section)

- **The CSP is Report-Only, not enforced.** It reports violations without blocking,
  so it cannot break login the way the previous enforced attempt did. It only
  becomes a control once you review the production violation reports and rename the
  header to `Content-Security-Policy`. Until then it is observability, not enforcement.
- **Copy-deterrence is UX only and trivially bypassed** — view-source, devtools, the
  network tab, or a plain `curl` all still read the rendered content. Nothing secret
  should ever rely on it. It raises effort for a casual visitor and nothing more.
- **Rate limiting is per-IP via slowapi.** Behind a shared proxy/CDN, IP keying can
  be coarse (many users → one IP, or one attacker → many IPs). It is solid
  brute-force friction, not a substitute for a WAF / bot management at real scale.
- **No email provider is integrated yet**, so although the verification/reset tokens
  are now masked in production responses, those flows are not actually deliverable in
  production until an email sender is wired in.
- **The full pytest suite was not re-run in this environment** — installing the
  backend dependencies exceeded the remote shell's time limits. All changed files
  pass `py_compile`, the rate-limit route signatures were verified statically, and
  the pre-change baseline was green. Run the suite in your own environment before
  deploying (see G).

## E. Architecture posture (brief)

FastAPI backend on Render (TLS terminated at the edge), Postgres on Neon, ORM-only
data access, JWT bearer auth with Argon2 hashing, server-side RBAC re-checks,
per-route rate limits, production API docs disabled, and a locked-down CSP on JSON
responses. Next.js frontend on Vercel with a security-header baseline (HSTS,
nosniff, frame-deny, referrer policy, permissions policy) plus the new Report-Only
CSP. Secrets are environment-injected, never in the repo.

## F. Before / after — relative score

These numbers are a **subjective, relative** read to show movement, not an audited
certification.

| Area | Before | After |
|------|:------:|:-----:|
| Authentication & password handling | 8/10 | 9/10 |
| Access control (RBAC / IDOR) | 9/10 | 9/10 |
| Secrets management | 6/10 | 8/10 |
| Endpoint exposure (docs / schema / bulk) | 4/10 | 8/10 |
| Abuse resistance (brute force / scraping) | 2/10 | 8/10 |
| Security headers / transport | 6/10 | 8/10 |
| **Overall** | **~68/100** | **~86/100** |

The biggest gains are in abuse resistance (from effectively none to per-route limits)
and endpoint exposure (docs closed, bulk cap tightened). The gap to a higher score is
mostly: enforcing the CSP after review, an email provider, and edge-level bot/WAF
protection.

## G. Testing & verification performed

- `py_compile` passes on every changed backend file.
- Rate-limited routes confirmed to carry the required `request: Request` parameter.
- `next.config.mjs` passes `node --check`.
- Production token-masking confirmed in `routes_auth.py`.
- Production docs-disable and the SECRET_KEY guard were code-reviewed.
- **Not done here:** the full pytest suite (dependency install exceeded the remote
  shell limits). The prior baseline (`test_account_security`, `test_auth`,
  `test_applications`) was green before these changes; re-run the suite before deploy.

---

*This document describes risk reduction, not a guarantee of security. Treat the
Report-Only CSP and the copy-deterrence layer as works-in-progress and deterrents
respectively, and run the test suite in a full environment before shipping.*
