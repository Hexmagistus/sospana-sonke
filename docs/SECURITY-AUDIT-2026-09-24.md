# Sospana Sonke: Architecture & Security Audit (24 September 2026)

Scope: full backend (FastAPI), frontend (Next.js), deployment config, and dependencies.
Method: read the code, inventory every route by its *actual* auth dependency (introspected from
the running app, not grepped), threat-model against the brief, fix what's fixable now, and write
down what isn't.

> Standing rule, borrowed from the last report: this document is about **reducing risk**. Nothing
> here makes the platform "unhackable". That word is reserved for sales decks and very brave people.

---

## 1. Architecture map

```
 Browser (Next.js 15 app on Vercel)          GitHub Actions
   │  JWT in localStorage, Bearer header        │  hourly parallel scanner (direct DB)
   ▼                                            │  cron → /cron/run/* (X-Cron-Secret)
 Render edge proxy (TLS, appends XFF)           │
   ▼                                            ▼
 FastAPI (uvicorn, 1 free instance) ───────► Neon Postgres (SQLAlchemy ORM, no raw SQL)
   ├─ auth: Argon2id, JWT HS256 (access 30m / refresh 14d), TOTP MFA, Google ID-token sign-in
   ├─ RBAC: role re-read from DB on every request (never trusted from the token)
   ├─ uploads: CV files, size-capped mid-read, magic-byte sniffed, extension allow-list
   ├─ email: Gmail SMTP (verification, reset, notifications, owner login alerts)
   ├─ payments: provider abstraction (mock | Paystack), HMAC-verified webhooks
   ├─ scraper: Greenhouse/Lever/SmartRecruiters/Recruitee/Workable/HTML, robots.txt, back-off
   └─ rate limiting: slowapi, in-memory (single instance)
```

Route inventory (introspected): **148 routes**. 107 require a signed-in user, 23 are admin-only
(`require_admin`, DB-verified), 1 has optional auth, 17 are public by design: auth flows, `/health`,
company icon redirect, tailor templates, comments summary, the HMAC-verified payment webhook, the
secret-guarded cron trigger, and 3 subscription routes that only ever return `410 Gone`.

## 2. Threat model: what I checked and where it landed

| Threat | Status |
|---|---|
| Brute force / password spraying | Per-IP limits existed but were **broken** (§3.1). Fixed, plus a new per-account lockout. |
| Credential stuffing (many IPs, one account) | **New:** 10 failures → 15-minute lock on that account. |
| Account enumeration | Login timing leaked "no such email" (no Argon2 work done). **Fixed.** Register still returns 409 for existing emails (accepted trade-off, see §5). |
| Session / token theft | Tokens couldn't be revoked at all. **Fixed:** token versioning + "Sign out everywhere". Tokens still live in localStorage (§5). |
| Password reset abuse | Reset links were reusable for 2 hours. **Fixed:** single-use, and a reset signs out every device. |
| IDOR / BOLA | Ownership checks are consistent across resource routes (re-verified in this pass). |
| Privilege escalation / mass assignment | Role is never accepted from input. Pydantic schemas don't expose `role`, `is_active` or `token_version`. OK. |
| SQL injection | ORM-only, no string-built SQL. OK. |
| XSS | React escapes by default. The only `dangerouslySetInnerHTML` is static JSON-LD. The CSP is still Report-Only (§5). |
| CSRF | Not applicable while auth is a Bearer header rather than a cookie (revisit if moving to cookies). |
| SSRF | Outbound fetches (scraper, URL tester, favicon discovery) only hit admin/seed-controlled company URLs. Admin-only triggers. OK. |
| Malicious uploads | Size-capped mid-stream, magic-byte check, extension allow-list, stored outside the web root. OK. |
| Payment fraud | **Found:** production runs the *mock* provider, whose signing secret is in this public repo, so anyone could forge "paid" webhooks. **Fixed.** |
| Bulk scraping of the directory | Any account can pull the whole directory in one call (the UI is built that way). **Mitigated** with per-account hourly limits. Real fix in §5. |
| Oversized requests / resource exhaustion | 30 MB global body cap, per-upload caps, list caps. OK. |
| Vulnerable dependencies | Backend: `pip-audit` clean. Frontend: **Next 14.2.15 had 2 critical + many high advisories** (incl. remote code execution in the image optimizer). **Fixed:** upgraded to Next 15.5.26 + React 19; `npm audit` now reports 0 vulnerabilities. |
| Secrets exposure | No live secrets in the repo; production refuses to boot on the placeholder `SECRET_KEY`; API docs disabled in production. OK. |

## 3. Fixed in this pass

1. **Rate limiting was effectively global (critical).** uvicorn only trusts `X-Forwarded-For`
   from 127.0.0.1, so behind Render every visitor appeared to share one IP, the proxy's. The
   "10 logins per minute per IP" limit was really "10 logins per minute for the whole of Africa",
   so one bored attacker could lock everyone out of sign-in. The limiter now keys on the
   proxy-appended (unspoofable) end of the XFF chain (`app/core/client_ip.py`,
   `TRUSTED_PROXY_HOPS=1`). Login-alert emails use the same trusted IP.
2. **Forgeable payments (high).** The mock provider now rejects every webhook when
   `ENV=production`, and card donations return a friendly 503 until Paystack is configured
   (instead of handing donors a dead `mock-pay.local` link).
3. **Session revocation (high).** `users.token_version` is embedded in every token as `tv`.
   Bumping it kills all access, refresh and reset tokens at once. Used by password reset, account
   deletion, and the new `POST /auth/logout-all` (a "Sign out everywhere" button on /security).
   Tokens issued before this change count as version 0, so **deploying it logs nobody out**.
4. **Single-use reset links.** They carry `tv`, so a completed reset invalidates the link and every
   other outstanding one.
5. **Per-account lockout + timing-safe login.** Unknown emails now burn a real Argon2 verification,
   so response time no longer reveals who has an account.
6. **Per-account bulk-read budgets.** `/companies` is capped at 60/hour and `/vacancies` at
   600/hour per account (keyed on the verified token, not the IP, so rotating IPs doesn't help).
7. **Next.js 14.2.15 → 15.5.26, React 18 → 19**, plus PostCSS pinned via `overrides`. Production
   build verified, all 32 routes prerender, and a runtime smoke test returns 200 on key pages with
   security headers intact.
8. **Bug found along the way:** four directory pages asked for 5,000 vacancies, but the API caps
   pages at 200, so the request 422'd, the page swallowed the error, and **vacancy counts never
   showed**. The pages now page through at 200 at a time (`api.getAll`).
9. The 4 long-failing tests (stale `reg["id"]` helper) are fixed. **The full backend suite is
   green for the first time in weeks.**

Schema: `users.token_version`, `users.failed_login_count` and `users.locked_until` are added through
the existing idempotent `_add_new_columns()` boot step. This was verified against a database that
predates them, with existing rows backfilled to 0/NULL.

## 4. Action needed from Lungani

- **Check the IP in the next login-alert email** against your real IP (search "what is my IP"). If
  it shows a 10.x/100.x address instead, Render adds a second proxy hop: set `TRUSTED_PROXY_HOPS=2`
  in Render and redeploy. That email is now a free diagnostic tool.
- **Click around once it deploys:** this is a framework major upgrade. Log in, browse companies and
  open a match. The build passed here, but eyeballs beat build logs. If anything looks off, Vercel →
  Deployments → the previous deployment → "Promote to Production" is an instant rollback.
- When Paystack goes live: set `PAYMENT_PROVIDER=paystack` + `PAYSTACK_SECRET_KEY` on Render, and
  card donations switch on by themselves.

## 5. Not done: roadmap, in priority order

1. ~~Server-side directory pagination/search~~: **done (follow-up pass, below).**
2. **Enforce the CSP** (it's still Report-Only), then consider **httpOnly cookie sessions** instead
   of localStorage tokens. That's a cross-site cookie + CSRF design across Vercel ↔ Render, so it's
   its own project.
3. **Edge protection:** a free Cloudflare proxy in front of the API (bot management, WAF, DDoS
   absorption). The free Render instance is the easiest way to take the platform offline today:
   it's one small instance, and it naps.
4. **Shared rate-limit store (Redis)** before ever running more than one backend instance. The
   in-memory counters are per-process.
5. **Admin audit log** (who changed match config, imported CSVs, sent suggestions).
6. **Real migrations (Alembic)** instead of the boot-time column adder.
7. **Backups:** confirm Neon point-in-time restore is enabled and actually test a restore.
8. **CI security gate:** `pip-audit` + `npm audit` + the test suite on every push.
9. ~~CV storage on Render's temporary disk~~: **done (follow-up pass, below).**
10. ~~Cron secret in the query string~~: fixed in the DAST follow-up (header-only now).

## 5b. Follow-up pass (same day): storage + directory scoping

**Durable file storage.** New `db` storage backend (`stored_files` table in the existing Neon
database; no new account or credential). `STORAGE_BACKEND=auto` (the new default) resolves to `db`
in production, so it switches on at deploy with no dashboard change. Files still sitting on
Render's disk are read from there once and copied into the database ("rescued") before the next
restart can wipe them. A download whose file was already lost now returns a friendly `410` ("please
re-upload") instead of a 500. Size note: Neon's free tier is 0.5 GB. Uploaded CVs are capped by
`MAX_UPLOAD_MB` and generated documents are ~40 KB, so this is comfortable for thousands of users. Move
to `s3` (e.g. Cloudflare R2) when that changes; the switch is one env var.

**POPIA erasure now covers documents.** "Delete my account" previously left CV files, extracted
CV text, generated CVs/cover letters and the candidate profile behind. It now deletes the stored
bytes and wipes/soft-deletes those records (`_erase_documents_and_profile` in `routes_account.py`).

**Directory scoping.** `GET /companies` gains `country`, `q` (LIKE-escaped), and `ids` filters.
Non-admin requests must be scoped and are capped at 1,500 rows (unscoped: 100). The per-account
budget is now 200 requests/hour. New `GET /companies/facets` (counts only, for tabs and headline
stats) and `GET /companies/surprise`. The Companies page loads one country/federations/shortlist
slice at a time (cached per slice). The Career Agent fetches only the slice a question needs, or
does server-side name search per keyword. Admin tools keep full access.

*Honest limit:* the directory's whole purpose is to be shown to signed-in users, so a determined
account can still page through it country by country. The difference is that this now takes ~60
rate-limited, logged requests instead of one silent one.

Verified end-to-end: API in production mode with the full 2,985-row seed, the built Next.js app, and
headless Chromium. Real form login → Companies (facets + South Africa slice only) → switch to
Botswana (one scoped request) → Career Agent "bank jobs in Botswana" answered with Botswana
employers; zero page errors; the UI never requested an unscoped list.

## 6. Verification

- Backend: full pytest suite green, including 11 new tests in `tests/test_security_controls.py`
  (IP resolution & spoofing, lockout, enumeration parity, logout-all, legacy tokens, single-use
  reset, production payment guards, per-user rate-limit keys).
- Frontend: `tsc --noEmit` clean; `next build` succeeds (Google Fonts stubbed in a scratch copy
  only, because this sandbox can't reach fonts.googleapis.com; the real `layout.tsx` is untouched);
  `next start` smoke test OK.
- Dependencies: `pip-audit` 0 known vulns; `npm audit` 0 vulnerabilities.
- **DAST (dynamic attack scan):** HawkScan needs a StackHawk account + API key, so the same class
  of scan was run with **OWASP ZAP 2.16.1** (free, no account) against a local copy of the API.
  Authenticated as a test candidate, all 122 remaining OpenAPI paths were imported and attacked
  (~70,000 requests: SQL/NoSQL/command injection, XSS, path traversal, SSRF probes, header
  fuzzing). The session-ending endpoints were excluded after the scanner's first run pressed
  "sign out everywhere" on itself, which confirmed that revocation works.
  - **Result: 0 high, 0 medium.** 1 low: user-supplied text is echoed in JSON. That is
    acceptable because JSON responses carry `nosniff` + `default-src 'none'` and React escapes on
    render.
  - **Found and fixed:** text containing control characters (NUL etc.) crashed CV/cover-letter
    `.docx` generation with a 500. This also affects real PDFs with odd bytes, not only attackers.
    All renderers now strip XML-illegal characters (`_xml_safe` in `documents/render.py`).
  - **Found and fixed:** the cron secret was accepted as `?token=` in the URL, where it leaks into
    logs. The endpoint is now header-only and rate-limited to 30/min.
  - **Access-control matrix** (separate scripted check): all 23 admin routes return 403 to a
    candidate; no private route answers without a login; a second candidate trying to read, edit,
    delete or list the first candidate's tailored applications and watches gets 404 every time.
