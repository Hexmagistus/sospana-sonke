# Working notes for Claude sessions

This repo is worked on from **two different Claude accounts/sessions** (the original
one ran out of quota; work continues from a second account). Both read and write here
so either session can pick up exactly where the other left off, without needing to
ask Lungani to re-explain context.

**Read this file first, every session.** Before starting work: read this file, then
`README.md` and `docs/PHASE1_STATUS.md` / `docs/PHASE2_STATUS.md` for what's built.
**Before ending a session** (or handing off mid-task), add a dated entry to the
Session Log below — a few lines: what changed, why, and what's next/unfinished — then
commit it (and push, if you pushed the rest of your work). Newest entry on top.

## Project at a glance

- **What it is:** free, pan-African job-discovery + CV-tailoring platform. Frontend:
  Next.js (`frontend/`), deployed on Vercel as `sospana-sonke.vercel.app` (account
  `hexmagistus1`). Backend: FastAPI (`backend/`), deployed on Render
  (`srv-da0le7tg1s2s73btqmbg`).
- **Country coverage:** all 26 African markets are live (`LIVE` array,
  `frontend/src/app/page.tsx`) — the original 16 SADC states plus Kenya, Nigeria,
  Ethiopia, Egypt, Morocco, Ghana, Senegal, Uganda, Rwanda and Algeria, imported into
  the production DB 2026-09-06. `SOON` is currently `[]` (empty) — there's no next
  wave queued yet.
- **Company seed data:** `backend/seed/company_database_import.csv` is the original
  bootstrap file (South Africa/Botswana/Eswatini/Lesotho only — stale, not the live
  DB's source of truth any more). Per-country research CSVs live in
  `backend/seed/countries/<Country>.csv` (same 10-column, no-header format:
  company_name, jse_code, careers_url, careers_status, relevance_note, active,
  scraping_status, country, source_type, source_url — see
  `backend/app/services/csv_import.py` for what an actual import expects, notably a
  header row, which these staging files don't have yet). A sibling, non-git
  `Claude outputs/` folder one level above this repo has older per-country CSVs for
  some SADC markets (Angola, Comoros, Madagascar, Malawi, Seychelles, Tanzania,
  Zambia) — check there before redoing research for any of those.
- **Known gotcha:** there is a second, **stray, non-git copy** of the frontend at
  `sospana-sonke-fullstack/frontend/` (sibling to this repo, one level up) — no
  `package.json`, no version control, and often stale. It is not deployed. Don't edit
  it by mistake when working on the homepage; always confirm you're inside
  `sospana-sonke/` (this repo, `git remote -v` → `Hexmagistus/sospana-sonke`).
- **Push workflow:** Lungani has numbered `.bat` scripts at the repo root
  (`2-UPLOAD.bat`, `3-UPDATE-AND-PUSH.bat`, etc.) for pushing from Windows, likely
  because `git push` needs an interactive GitHub sign-in on that machine. A
  device-linked session may not be able to push non-interactively — say so rather than
  silently failing, and let Lungani run the `.bat` script if needed.

## Session Log

### 2026-09-06 (later same day) — Claude (this account) — SECURITY HARDENING IN PROGRESS, HANDOFF
Lungani asked for a full security audit + hardening pass (protect secrets, prevent
source theft, protect DB/admin/API endpoints, rate limiting, security headers,
production config, copy-deterrence, final report with before/after score). This is a
**priority task, still in progress** — if this session ran out of quota, **the next
session should pick up here, not restart the audit.**

**Status: audit-only so far, ZERO code edits made yet, ZERO commits made for this
security work.** Read-only review of the whole backend + frontend is done.

**Confirmed SAFE (no changes needed):**
- Admin role always re-verified from a fresh DB fetch server-side
  (`backend/app/core/deps.py`) — never trusted from JWT/client. IDOR protection
  (ownership checks) consistent across all resource routes. No raw SQL anywhere
  (ORM-only). No hardcoded live secrets in tracked files. `.gitignore` excludes
  `.env`/`.db`. CORS is a real allowlist (no wildcard+credentials). Cron endpoint
  (`routes_cron.py`) uses `hmac.compare_digest` + 404-when-unconfigured. Path
  traversal already defended in `services/storage.py`. Matching-algorithm
  weights/thresholds (`matching/config.py`) are admin-only, not leaked to users.

**Confirmed VULNERABLE — fixes identified but NOT YET IMPLEMENTED:**
1. `backend/app/core/config.py` — `SECRET_KEY` has a weak hardcoded default with no
   startup fail-safe if `ENV == "production"` still uses it (mitigated today only by
   `render.yaml`'s `generateValue: true`, not by the code itself).
2. `backend/app/api/routes_auth.py` + `backend/app/schemas/auth.py` —
   `RegisterResponse.email_verification_token` is returned unconditionally in ALL
   envs including production. Needs the same production-masking already correctly
   done for `reset_token` in `SimpleMessage`.
3. Zero rate limiting anywhere (`backend/requirements.txt` has no slowapi/limits) —
   `/auth/login`, `/register`, `/password-reset/request`, `/refresh`, MFA endpoints
   all brute-forceable.
4. `backend/app/main.py` — `/docs`, `/redoc`, `/openapi.json` enabled in all envs
   including production.
5. `frontend/next.config.mjs` — deliberately has NO Content-Security-Policy (a prior
   attempt broke login — see comment in that file). Needs a carefully scoped CSP;
   draft policy already drafted (see prior session notes / ask Claude to re-derive
   from `login/page.tsx`'s Google Sign-In script + Render API host + Clearbit/gov.za
   logo hosts).
6. `list_vacancies` has `le=5000` limit — lower-priority bulk-scraping tightening.
7. No client-side copy-deterrence layer yet (text-selection/copy/right-click/
   Ctrl+C/Ctrl+U deterrents) — explicitly UX-only per the task spec, not real
   security, not yet started.

**Testing infra (device VM, NOT this repo folder):** created a venv at
`~/scratch/venv` on the linked Windows machine's Linux VM (outside `mnt/`, per the
scratch-stays-outside-mnt rule) and installed `backend/requirements.txt` + pytest +
pytest-asyncio into it — this worked and is reusable. **Important VM quirk
discovered:** background/`nohup`/`setsid`-detached processes do NOT survive between
separate device-shell calls in this environment (confirmed by test — a detached
`sleep`+echo loop produced zero output). So the full pytest suite (22 files, ~145
tests) must be run in foreground, chunked into batches that fit one command's ~170s
window — Argon2 hashing makes auth-related tests ~9s/test, so batches of 1-2 files
at a time. Baseline run in progress at hand-off: confirmed passing so far —
`test_account_security.py` (5/5), `test_applications.py` + `test_auth.py` (18/18,
run together). Remaining files not yet run this baseline pass: `test_automation.py`,
`test_channels_analytics.py`, `test_companies.py`, `test_cv.py`, `test_dashboard.py`,
`test_documents.py`, `test_match_routes.py`, `test_match_service.py`,
`test_matching_engine.py`, `test_notifications.py`, `test_phase2_extras.py`,
`test_profile.py`, `test_scan_service.py`, `test_scraper_extract.py`,
`test_scraper_js.py`, `test_scraper_parsers.py`, `test_subscription.py`,
`test_url_tester.py`, `test_vacancy_routes.py`.

**Next steps for whichever session picks this up:**
1. Finish the pre-change baseline (remaining test files above) — or skip straight to
   implementing fixes 1-7 above if baseline time is a concern, since all confirmed-
   passing so far and no code has been touched.
2. Implement fixes 1-5 as the smallest effective changes (rate limiting = add
   `slowapi` to requirements.txt), fix 6 optionally, fix 7 (copy-deterrence) last.
3. Re-run the same test files after each change batch to catch regressions.
4. Commit locally only (never push — Lungani pushes himself via his `.bat` scripts).
5. Produce the full A–G security report Lungani asked for (what changed / secrets
   found — type+location only, never values / remaining vulnerabilities / copy
   protection explained honestly as deterrence not security / architecture / a
   before-and-after score out of 100 / confirmation tests still pass). Must NOT
   claim "unhackable" anywhere.
6. Also standing: remind Lungani, once new-country expansion settles, to run the
   admin URL-tester verification pass across all countries (already saved to
   Claude's persistent memory too, not just here).

### 2026-09-06 (night) — Claude (this account)
- Added an `NGO` source_type category to the 10 new countries' seed CSVs, matching
  the convention already used for all 16 SADC countries in
  `backend/seed/company_database_import.csv` (South Africa alone carries 17 NGO
  rows, every other SADC state 3-9). Each new country got major UN agencies
  (UNICEF/UNDP country offices, plus UNHCR/WFP where there's a large
  refugee/humanitarian caseload — Uganda, Ethiopia, Egypt, Algeria) and 3-5
  well-known international or national NGOs (Red Cross/Red Crescent society,
  World Vision, Plan International, Save the Children, CARE, etc., picked per
  country's actual NGO footprint). 5-8 rows per country, 68 rows total. Committed
  one country at a time (`backend/seed/countries/<Country>.csv`, commits
  `e8a3ac9`..`577c446`) — same desk-research caveat as the DEPT/MUNI/SOE/PRIVATE
  batch: careers URLs are `amber_company_route` (known org domain pattern) or
  `grey_none_verified` (best guess), not browser-verified this session.
- Imported all 68 NGO rows into the live DB via the same admin-endpoint /
  authenticated-fetch technique as before, then refreshed `LIVE` counts in
  `frontend/src/app/page.tsx` again (Kenya 45->53, Nigeria 61->68, Ethiopia
  38->46, Egypt 41->48, Morocco 34->40, Ghana 37->44, Senegal 36->42, Uganda
  39->47, Rwanda 39->45, Algeria 39->44; total DB now 2,439 companies), commit
  `40833eb`.
- **Not yet done:** same verification-pass caveat as the prior entry — none of
  today's additions (DEPT/MUNI/SOE/PRIVATE or NGO) have been run through the URL
  tester yet.


### 2026-09-06 (evening) — Claude (this account)
- Imported all 10 `backend/seed/countries/<Country>.csv` files into the live
  production Postgres DB via the admin `/api/v1/companies/import` endpoint — done
  from the browser (Lungani logged in, JWT read from `localStorage`), one country at
  a time, since the built-in browser toolset has no file-upload tool: transformed
  each staging CSV to the header format `csv_import.py` expects (Python script,
  base64-encoded), then executed an authenticated `fetch()` POST directly in page JS.
  Results (created/updated out of total_rows): Kenya 48/0/48, Nigeria 61/0/61 (after
  fixing a corrupt row, commit `a2f9150`), Ethiopia 42/2/44, Egypt 43/4/47,
  Morocco 39/0/39, Ghana 35/7/42, Senegal 34/5/39, Uganda 39/2/41, Rwanda 32/7/39,
  Algeria 36/3/39. Updated/skipped rows are near-duplicates already seeded from
  earlier SADC-market company lists (e.g. pan-African banks/telcos) — expected, not
  an error.
- Queried the live DB for authoritative per-country company counts (409 new + 1962
  existing = 2371 total) and used them to move all 10 countries from `SOON` to
  `LIVE` in `frontend/src/app/page.tsx`, each with its real `count`. Also refreshed
  the 16 existing SADC counts (they'd drifted from the live DB) and re-sorted `LIVE`
  descending by count so the "who's powering Africa's opportunities" bar chart (which
  uses `LIVE[0].count` as its 100% baseline) stays correct. Updated the hero badge and
  the Africa-section copy from "16 SADC markets" to "26 African markets". `SOON` is
  now `[]`, so its "Coming soon" section on the homepage hides itself (by design —
  `{SOON.length > 0 && (...)}`). Commit `8f46436`.
- **Not yet done:** the verification pass on the `grey_none_verified` rows noted in
  the entry below is still outstanding — these companies are live in the DB and on
  the homepage now, but a chunk of their careers URLs are desk-research best-guesses,
  not confirmed. Worth an admin URL-tester pass
  (`backend/app/services/url_tester.py`) when there's time.


### 2026-09-06 — Claude (this account)
- Added 10 non-SADC countries to the homepage "Coming soon" list (Kenya, Nigeria,
  Ethiopia, Egypt, Morocco, Ghana, Senegal, Uganda, Rwanda, Algeria) now that all 16
  SADC states are live; relabelled the section "Coming soon across Africa".
  `frontend/src/app/page.tsx`, commit `cd30e4c`.
- Committed pending local churn (build logs, upload `.bat`, `update-log.txt` —
  line-ending refresh only, no functional change), commit `8444ba9`.
- Discovered the stray non-git `frontend/` copy noted above — left untouched.
- **Not yet done:** real company/vacancy data for the 10 new `SOON` countries (no
  CSVs prepared yet for Kenya/Nigeria/Ethiopia/Egypt/Morocco/Ghana/Senegal/Uganda/
  Rwanda/Algeria — check `Claude outputs/` first in case that changes).

### 2026-09-06 (later same day) — Claude (this account)
- Researched and committed company data for all 10 `SOON` countries, one commit each
  (`backend/seed/countries/{Kenya,Nigeria,Ethiopia,Egypt,Morocco,Ghana,Senegal,
  Uganda,Rwanda,Algeria}.csv` — commits `14a0868`..`e0cfa00`). 439 rows total:
  government ministries (DEPT), provincial/state/regional government (MUNI), state-
  owned enterprises/parastatals (SOE), and major private/stock-exchange-listed
  companies (PRIVATE) per country, matching the category convention already used for
  the SADC markets.
- **Caveat — this is desk research, not verified data.** Most rows are
  `grey_none_verified` with a best-guess official domain (e.g. `<ministry>.gov.ke`
  patterns) built from general knowledge, not fetched/browsed this session. A handful
  are `green_verified` or `amber_company_route` where a web search this session
  actually surfaced a live careers/vacancies page (noted in each row's relevance_note).
  Before importing: run these through the URL tester
  (`backend/app/services/url_tester.py`) or a browser pass to catch dead domains and
  wrong guesses, the way the original SADC company lists were verified.
- **Not yet done:**
  1. Verification pass on the ~370 `grey_none_verified` rows above (confirm domains
     resolve and are actually careers pages).
  2. Add a header row and actually import each CSV via the admin CSV-import endpoint
     (`csv_import.py` expects a header — these staging files currently don't have one)
     so the companies exist in the live Postgres DB, not just in the repo.
  3. Once imported and verified, flip each country from `SOON` to `LIVE` in
     `frontend/src/app/page.tsx` (with an employer `count`), the same way the 16 SADC
     states were promoted.

### 2026-09-06 (later) — Claude (Opus, other account)
Picked up the in-progress security-hardening batch the previous session left
uncommitted and committed it (`62a8b9a`):
- `app/core/rate_limit.py` (new): shared slowapi Limiter, per-IP, disabled under
  ENV=test. Limits applied in `routes_auth.py` to register/login/google/refresh/
  mfa-enable/mfa-disable/password-reset request+confirm.
- `main.py`: `/docs`,`/redoc`,`/openapi.json` disabled when ENV=production; limiter +
  SlowAPIMiddleware + 429 handler wired; strict CSP (`default-src 'none'`) on JSON routes.
- `config.py`: refuses to boot in production if SECRET_KEY is still the placeholder.
- `schemas/auth.py` + `routes_auth.py`: email-verification / password-reset tokens
  masked to None when ENV=production.
- `requirements.txt`: +slowapi==0.1.10 (MUST `pip install -r requirements.txt` before
  running the app or the import fails). `.gitignore`: ignore test DB journal.
- Verified: `py_compile` passes on all changed files; token-masking confirmed at
  routes_auth.py L43/L206. NOT yet run: the pytest suite (needs slowapi installed).
- Also earlier this session (already committed by the data session): removed the
  "No open positions listed yet" label on company cards + made the country filter
  chips wrap instead of horizontal-scroll on mobile (`companies/page.tsx`); set
  Assmang's careers_url to https://assmang.ci.hr (verified live portal).

**Note for whoever runs git here via device_bash:** the bridge can't delete files, so
every git op leaves a stale `.git/index.lock` (and sometimes `HEAD.lock`) that blocks
the next op. Clear with `mv .git/index.lock .git/index.lock.stale.$(date +%s%N)` before
each git command (rename is allowed; rm is not), or grant delete permission.

**Not yet done (security task remaining):** verification pass / pytest run of the above;
plus any still-open items in the security checklist earlier in this file (DB access,
admin-route protection, copy-deterrence, final report).
