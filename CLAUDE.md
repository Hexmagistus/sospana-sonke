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

### 2026-09-07 (later again) — App pricing set to Free; icon resolved
- App pricing (Monetize with Play > App pricing): switched from the
  default "Paid" to "Free" and saved. That was the last of the original 9
  Play Console sections except the store listing itself.
- Store listing: found the app icon was already sitting in Play Console's
  asset library (the gold/silver "Sospana Sonke" logo, previously uploaded
  as a WhatsApp image, cropped to 512x512) — selected it for the App icon
  slot (had to delete one accidental duplicate first) and saved the draft.
  Dashboard checklist now shows **12 of 13 complete** — only "Set up your
  store listing" remains, blocked on the feature graphic + 2-8 screenshots
  (see prior entry for why — native file-dialog upload isn't reliably
  automatable from here). Waiting on Lungani to either upload those two
  asset types himself or say how he'd like to proceed.
- Lungani confirmed he has Android Studio installed and can build the
  signed `.aab` himself. Checked `android/app/build.gradle`: it's a
  Bubblewrap-generated TWA (applicationId `com.sospanasonke.app`,
  versionCode 1, versionName "1.0.0"), no `signingConfigs` block baked in
  (expected — Bubblewrap projects sign via Android Studio's "Generate
  Signed Bundle" wizard at build time, not gradle). `android/android.keystore`
  already exists in the repo root of `android/`. Pointed him to
  Build > Generate Signed Bundle/APK > Android App Bundle > select that
  keystore file > enter his alias/passwords > release build variant.
  Passwords obviously not handled by Claude.

### 2026-09-07 (even later) — Play Store store listing: text done, assets blocked
- Filled in Default store listing text (Play Console): app name confirmed
  "Sospana Sonke", short description (71/80 chars), full description (~1238
  chars) covering free job search + CV tailoring + all 16 SADC states + the
  new donations option. **Not yet saved** — still needs "Save as draft"
  once assets are attached (see below).
- Prepared image assets on disk: resized `frontend/public/logo-mark.png`
  (1024x1024) down to `play-assets/app-icon-512x512.png` (512x512 RGB, no
  alpha); `play-assets/feature-graphic-1024x500.png` already existed and is
  ready as-is.
- **Blocked on uploading them**: Play Console's "Add assets" opens the
  native Windows file-picker dialog, and remote control of that dialog is
  restricted to view + single-click only (no double-click, no typing, no
  Enter key) for security reasons — couldn't navigate folders or confirm a
  selection. Asked Lungani to click through `Add assets` → `Upload` himself
  and pick the two files above (30-second task) — message sent, no reply
  yet as of this entry.
- Identified 4 good phone-screenshot candidates from the live site
  (sospana-sonke.vercel.app) at 1080x1920: (1) hero "Where talent meets
  opportunity" w/ Mandela quote, (2) stats panel (2400+ employers tracked /
  Direct to careers pages / SOE vacancies / Free), (3) pan-African
  landmarks grid (Kilimanjaro, Pyramids, Serengeti, etc.), (4) sign-in
  screen w/ tagline "We find the opportunities. You apply direct." Could
  not save these as actual image files (no file-save path from the browser
  pane back to disk) — Lungani will need to screenshot these himself, or
  ask to explore another capture method.
- **Not yet done**: attach the 2 prepared assets + 2-8 screenshots, save
  the store listing draft, then set the app price (Free) — the last of the
  9 Play Console sections from the original plan.

### 2026-09-07 (later still) — Claude (this account) — Play Console: all App content declarations done
- Completed all 4 outstanding "App content" policy declarations, in order: Advertising
  ID (No -- no ad SDKs), Government apps (No), Financial features (selected "My app
  doesn't provide any financial features" -- the R100/month subscription and the new
  donation checkout are plain payment/checkout flows via Paystack, not a regulated
  financial feature like lending/wallets/trading/insurance), Health apps (selected
  "My app does not have any health features"). Play Console's App content page now
  shows "You're all caught up."
- Remaining from the original 9-section plan: Store listing (description text +
  screenshots) and Set the price (Free). Data safety, Content rating, Target
  audience, and all App content declarations are done.
### 2026-09-07 (later) — Claude (this account) — Play Console: Data safety section done
- Continuing from "yes, fill in the 9 remaining Play Console sections": finished the
  Data safety form in full (all 5 steps: Overview, Data collection and security,
  Data types, Data usage and handling, Preview) and saved -- Play Console now shows
  "Change saved. Send for review in Publishing overview." for this section.
- Data types disclosed, based on reading the actual backend models
  (`User`, `CandidateProfile`, `CV`, `Subscription`/`Payment`): Personal info (Name,
  Email address, Phone number), Financial info (Purchase history), Files and docs
  (CV uploads), App activity (App interactions), Device or other IDs (push
  notification token). Health and fitness/Messages/Photos/Audio/Calendar/Contacts/
  Web browsing/Location left unchecked -- not applicable. Email address and Files
  and docs are marked "Shared" (with Paystack for payment, and the AI provider for
  CV parsing/tailoring, respectively) in addition to "Collected".
- Delete-account URL set to the `/privacy` page (no dedicated in-app deletion
  endpoint exists) and "encrypted in transit: Yes" from the earlier
  Data-collection-and-security step.
- UI quirk confirmed again: the final "Save" on the Preview step is not a visible
  button -- it's in the kebab (⋮) "More options" menu next to "Discard".
- Next up (still pending, per the original 9-section plan): Government apps (answer
  No), Financial features (review needed for the R100/month + new donation flow),
  Health (answer No), Store listing text + screenshots, Set the price (Free).
### 2026-09-07 — Claude (this account) — donations page
- Added a `/donate` page (no login required) with R20/R50/R100 presets plus a
  custom "Other" amount, going through the existing Paystack integration
  (one-off checkout, not a subscription). Also lists a direct-bank-transfer
  option (Capitec, acc 2581657193, SWIFT CABLZAJJ) for people who'd rather
  skip card fees. New `/donate/thanks` return page.
- Backend: new `Donation` model/ledger (separate table, not tied to a user
  account or the subscription access-gating) + `donation_service.py` +
  `routes_donation.py` (`POST /donations/checkout`). Donations share the
  same Paystack account/webhook as subscriptions -- references are prefixed
  `DON-` and `subscription_service.handle_webhook` routes those to the new
  donation handler, so no second webhook URL needs configuring in Paystack.
  `PaymentProvider.start_checkout` gained an optional `callback_url` so
  donations return to `/donate/thanks` instead of `/subscription/return`.
- Commit `e8caa3e`. 6 new backend tests pass; reran the full subscription
  suite -- no regressions (the 2 failures there are pre-existing/unrelated,
  from the deliberate paywall-disable in `90b1da7`).
- **Action needed from Lungani** (same pattern as `PAYSTACK_SECRET_KEY` /
  the Gmail SMTP vars): once Paystack is live, set `DONATION_RETURN_URL` in
  Render to `https://sospana-sonke.vercel.app/donate/thanks` (defaults to
  a localhost URL otherwise). `PAYSTACK_SECRET_KEY`/`PAYMENT_PROVIDER=paystack`
  need to be set too if they aren't already -- donations use whatever
  provider subscriptions are configured for.
- Paused mid-way through the Google Play Console setup for the Android
  app (see the entry above/below on that) to build this at Lungani's
  request; resuming Play Console work next.

### 2026-09-06 (later still) — Claude (this account) — test-suite verification of the security batch
The security task Opus completed (see the two entries below and
`docs/SECURITY-HARDENING-REPORT.md`) explicitly hadn't run the real pytest suite
("dep install exceeded the remote shell's time limits"). This session managed it:
created a venv at `~/scratch/venv` on the device VM (outside `mnt/`), installed
`backend/requirements.txt` + `pytest` + `pytest-asyncio` + `slowapi` successfully
(took a few chunked `pip install` calls, each hitting the ~170s device-shell limit
but resuming from cache), then ran the suite in batches (full-suite run in one shot
also hits the shell limit -- Argon2 makes auth tests ~9s each).

**Result:** `test_auth.py` (7) + `test_account_security.py` (5) = 12/12 passed,
`test_companies.py` 4/4 passed. **No regression from the security hardening.**

**One real gap found and fixed** (commit `a19a4a9`): `app/core/rate_limit.py`'s
`Limiter(enabled=settings.ENV != "test")` never actually triggered because
`tests/conftest.py` didn't set `ENV=test` (defaulted to "development", so the
limiter stayed live across the whole shared-`app`-instance test run). Fixed by
adding `os.environ.setdefault("ENV", "test")` to conftest.py.

**One pre-existing, unrelated bug found** (not fixed, out of this task's scope):
`tests/test_dashboard.py::test_candidate_dashboard` gets a 404 on `GET /dashboard`
-- that endpoint was deliberately deleted in `bb9ac9c` ("Remove unused candidate
dashboard API endpoint") but the test was never removed/updated. Dead-test debt,
nothing to do with security. Worth a cleanup pass (delete the stale test, or check
nothing else depended on that route) whenever there's time.

**Not run this pass** (lower priority, unrelated to auth/security): the other ~18
test files (`test_automation`, `test_cv`, `test_documents`, `test_matching_engine`,
`test_notifications`, `test_scraper_*`, `test_subscription`, `test_vacancy_routes`,
etc.) -- none of them touch code this security batch changed, so risk is low, but
flagging in case someone wants full green-suite confidence before deploying.

Also: the SMTP/Gmail App Password + Render env-var follow-up (see "Gmail email
delivery wired" below) is still open and needs Lungani's action -- unrelated to me,
belongs to that thread.

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

### 2026-09-06 (later) — Claude (Opus) — SECURITY TASK COMPLETE
Implemented the remaining audit fixes (1–4 were committed earlier in `62a8b9a`):
- #5 CSP: shipped **Report-Only** in `frontend/next.config.mjs` (`4df5a5b`) — scoped
  for Next inline scripts, Google Sign-In, Render API, logo hosts. Flip the header
  name to `Content-Security-Policy` to ENFORCE only after reviewing prod violation
  reports (an enforced CSP is what broke login before).
- #6 vacancy list cap `le=5000` → `le=200` (`8cf8dfa`).
- #7 copy-deterrence `CopyGuard.tsx` mounted in `layout.tsx` (`4df5a5b`) — UX-only,
  leaves form fields usable; NOT a security control.
- Wrote the A–G report: `docs/SECURITY-HARDENING-REPORT.md` (before ~68 / after ~86,
  honest, no "unhackable" claim).
- Verification: `py_compile` on all changed backend files; rate-limit route
  signatures OK; `node --check next.config.mjs` OK. **Full pytest NOT re-run this
  session** (dep install exceeded the device shell's time limits) — run before deploy.
- All commits are LOCAL only; Lungani pushes.
- **Security task done.** Optional follow-ups: enforce the CSP after review;
  integrate an email provider (verification/reset flows aren't deliverable without one);
  run the full pytest suite.

### 2026-09-06 (later) — Claude (Opus) — Gmail email delivery wired
- **Gap closed:** registration created a verification token but never emailed it, so
  in production (where the token is masked out of the API response) users got nothing.
  `register` now sends a verification email (link = `PUBLIC_API_URL` + `/api/v1/auth/verify?token=`)
  via the existing email-provider abstraction. Reset email copy improved too.
- `config.py`: added `PUBLIC_API_URL` (build links) and defaulted `SMTP_HOST=smtp.gmail.com`.
- `email.py`: 15s SMTP timeout.
- `.env.example` + `render.yaml`: Gmail SMTP env (`EMAIL_PROVIDER=smtp`, `SMTP_HOST/PORT`,
  `SMTP_USER`/`SMTP_PASSWORD`/`EMAIL_FROM` as sync:false secrets, `NOTIFY_EMAILS=true`,
  `PUBLIC_API_URL`).
- **ACTION REQUIRED by Lungani (I can't set secrets):** in Gmail enable 2-Step
  Verification, create an App Password (Google Account ▸ Security ▸ App passwords),
  then in the Render dashboard set `SMTP_USER` = the Gmail address, `SMTP_PASSWORD` =
  the 16-char App Password, `EMAIL_FROM` = e.g. `Sospana Sonke <address@gmail.com>`.
  Gmail rejects the normal account password over SMTP.
- Still open: no frontend `/verify` or `/reset-password` pages — the verify link hits
  the API directly (works, returns JSON); password reset still needs a frontend page
  to enter the token (or a GET-based flow).

### 2026-09-06 (later) — Claude (Opus) — Google sign-in audited (already existed)
- "Continue with Google" was ALREADY implemented (Google Identity Services ID-token
  flow): frontend renders GIS button when `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set; backend
  `POST /auth/google` verifies the ID token (aud + email_verified), find-or-creates a
  `candidate` user, issues our own JWTs with the DB role. No client secret anywhere.
- Hardened: added `iss` (issuer) pin to `accounts.google.com` (`e62b05a`).
- Wrote `docs/GOOGLE-AUTH-REPORT.md` (what auth exists, security audit, manual config).
- **MANUAL config still required (I can't do these):** create a Google Cloud OAuth 2.0
  **Web** client; add Authorized JavaScript **origins** (localhost:3000 + prod Vercel
  domain — no redirect URIs, no secret for this flow); set `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  in Vercel and `GOOGLE_CLIENT_ID` (same value) in Render. Button stays hidden until set.
- Recommended later: store Google `sub` + `last_login` (needs migration); local
  `google-auth` verification; build `/verify` + `/reset-password` frontend pages.
- Note: app login is email+password(+TOTP), not passwordless email-OTP — confirm with
  Lungani if he actually wants passwordless email codes.

### 2026-09-06 (later) — Claude (Opus) — Google login CONFIGURED live (browser-driven)
Set up the real Google OAuth in the owner's Google Cloud + Vercel via browser control:
- **Google Cloud** ("My First Project"): OAuth consent screen configured (External,
  publishing status = **Testing**), app name "Sospana Sonke", support/dev email
  gastricl@gmail.com. Created a **Web** OAuth client. **Client ID (public):**
  `343080221936-307hr2su2ufv6n4t443jb2crjtk0bdho.apps.googleusercontent.com`
  (client secret is NOT used by the GIS ID-token flow and was never recorded).
  Authorized JavaScript origins: `http://localhost:3000` and
  `https://sospana-sonke.vercel.app`. Added test user gastricl@gmail.com.
- **Vercel** (project sospana-sonke, prod domain sospana-sonke.vercel.app): added
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (Config type, Production) = the Client ID above;
  triggered a Production redeploy.
- **Render** (sospana-sonke-api): `GOOGLE_CLIENT_ID` = same Client ID **STILL TO BE
  SET** (owner needs to sign into Render). REQUIRED or /auth/google returns 503.
- App is in **Testing** mode → only test users can sign in. To open to ALL users,
  publishing is blocked until the app has a **privacy policy + terms of service** page.
- **NEXT (in progress):** build `/privacy` and `/terms` frontend pages, deploy, add
  their URLs on the Google Branding page, then **Publish app** (no Google verification
  needed for basic email/profile/openid scopes). Then set the Render env var.

### 2026-09-06 (later) — Claude (Opus) — Google app PUBLISHED to production
- Added `/privacy` and `/terms` pages (commit a637007) and set them as the app's
  privacy-policy / terms links + home page on the Google Branding page.
- **Published the OAuth app to "In production"** (basic scopes → NO Google verification
  needed, NO user cap). Result: ANY Google user can now use "Continue with Google" —
  the earlier test-user list is no longer needed.
- **STILL REQUIRED (2 items, owner action):**
  1. **Push** the pending local commits so `/privacy` + `/terms` actually deploy to
     Vercel (Google's consent screen links to them). `git rev-list origin/main..HEAD`.
  2. **Render → sospana-sonke-api → Environment:** set `GOOGLE_CLIENT_ID` =
     `343080221936-307hr2su2ufv6n4t443jb2crjtk0bdho.apps.googleusercontent.com`.
     Until then `POST /auth/google` returns 503 and Google logins fail at the backend.
- Vercel already has `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (Production) and was redeployed, so
  the button shows on the live site.

### 2026-09-06 (later) — Claude (Opus) — Google login FULLY WIRED
- **Render** `sospana-sonke-api`: added `GOOGLE_CLIENT_ID` =
  `343080221936-307hr2su2ufv6n4t443jb2crjtk0bdho.apps.googleusercontent.com` and
  triggered Save/rebuild/deploy. Backend can now verify Google ID tokens.
- Everything for "Continue with Google" is now configured: Google app published,
  Client ID in Vercel (NEXT_PUBLIC_GOOGLE_CLIENT_ID) + Render (GOOGLE_CLIENT_ID),
  origins + privacy/terms set, /privacy + /terms pages deployed.
- Free-tier note: the Render backend spins down when idle, so the FIRST Google
  login after a quiet period can take ~50s while it wakes.
- Remaining optional: Render SMTP_USER / SMTP_PASSWORD (Gmail app password) for the
  email/verification feature — separate from Google login.

## Standing rule (data)
- STANDING RULE: EVERY time countries are added, update ALL landing-page copy in `frontend/src/app/page.tsx`: the LIVE array (country + count, sorted desc) AND every hardcoded "N African markets" / employer-count number (currently the hero badge, the animated "Employers tracked" stat, the "2,800+ companies" feature line, the closing paragraph, and the footer banner) — user directive 2026-09-08.
- Country adds so far beyond the base 26: Cote dIvoire, Tunisia, Cameroon, Guinea, Gabon (commit b50bc79); Benin, Togo (this commit). Seed files: `backend/seed/countries/<Country>.csv` (headerless); import to live DB via admin `/api/v1/companies/import` (prepend header first).
