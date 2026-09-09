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
- **Country coverage:** all 54 African nations are live in the `LIVE` array
  (`frontend/src/app/page.tsx`) as of 2026-09-09 — see the Session Log for the
  full history of batches. `SOON` is `[]` (empty) — coverage is complete, nothing
  queued. **Caveat: "live" here means the seed CSV exists in
  `backend/seed/countries/` and the landing page reflects it — most of these
  countries (everything with `pending: true`) have NOT actually been imported into
  the production Postgres DB yet.** Only the original 16 SADC states plus the 10
  countries imported 2026-09-06 are confirmed live in the real database.
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
### 2026-09-09 — Claude (this account) — FULL 54/54 AFRICAN COVERAGE REACHED
- User asked "how many countries left?" then "add all of them across all
  categories and update the get started page" — finished the remaining 12
  uncovered African countries in one pass: **Burundi, Cabo Verde, Central
  African Republic, Congo (Brazzaville), Djibouti, Equatorial Guinea,
  Eritrea, Libya, Sao Tome and Principe, Somalia, South Sudan, Sudan.**
  Every one of the 54 UN-recognized African states now has a seed CSV in
  `backend/seed/countries/`.
- Same 12-agent parallel research process, same verification-honesty
  convention. Several of these are genuinely hard cases and were researched
  candidly rather than padded:
  - **Eritrea: only 4 rows** (1 DEPT, 3 NGO, 0 PRIVATE, 0 SOE) — the
    thinnest file in the whole database. One-party state, near-total
    internet isolation; only the state news portal and UN
    country-team/UNDP/WHO pages have any real web presence at all. No bank,
    telecom, or SOE website could be verified to exist.
  - **Equatorial Guinea: 10 rows**, 0 PRIVATE — ExxonMobil/Marathon have
    exited, GEPetrol has no resolvable domain.
  - **CAR: 15 rows**, only 1 SOE (ENERCA, and even that's a squatted-domain
    situation — real presence is a third-party customer portal).
  - **Sudan (15) and South Sudan (16):** conflict-context caveats on most
    rows; several government sites down, hijacked-looking, or redirect-loop
    broken; UNHCR Sudan confirmed relocated to Port Sudan.
  - **Libya (27):** GNU/Tripoli-based government flagged per-row given the
    divided-government situation; 10 SOE rows (oil-sector heavy) but only 1
    PRIVATE survived verification.
  - **Somalia (20):** unusually NGO-heavy (7) given the humanitarian
    context, but has a genuinely vibrant verified private mobile-money/telco
    sector (Hormuud, Golis, Premier Bank, Amana, Salaam Somali Bank).
  - Congo-Brazzaville (32), Cabo Verde (30, notably clean — Portuguese
    government portal + public-employment site all verified), Burundi (27),
    Djibouti (23), Sao Tome and Principe (19) were all comparatively
    straightforward.
  - Commit `4402671`: 238 rows across the 12 files.
- Landing page rewritten for full coverage, not just another incremental
  batch: hero badge and footer banner no longer say "growing" / "more to
  follow" since there's nowhere left to add — now "Live across all 54
  African nations · The full continent, one platform." LIVE array now has
  all 54 entries (sum 3439), sorted descending, verified no dupes. Employers
  stat 3201->3439, feature line 3,000+->3,400+. `tsc --noEmit` clean.
  Commit `6464c0a`.
- Checked for a separate "get started" page per the user's request — there
  isn't one; "Get started" is just the CTA button label on this same
  landing page (`frontend/src/app/page.tsx`, linking to `/register`), which
  is what got updated above.
- **What's left (same recurring items, now covering all 21 non-original
  countries added since the SADC-completion baseline):**
  1. **DB import still blocked — needs Lungani's admin login** (see the
     entries above for the exact `/api/v1/companies/import` procedure).
     All 21 CSVs from the last 2 days of sessions need this.
  2. Verification pass on the accumulated `grey_none_verified`/
     `amber_company_route` backlog — now larger than ever; a single
     admin URL-tester sweep across everything would be more efficient than
     re-verifying piecemeal per country.
  3. **Push:** now 8 commits ahead of `origin/main` (`fc27ae1` through
     `6464c0a`) — still needs Lungani's interactive GitHub login.
  4. Consider whether `SOON` messaging elsewhere in the app (not just this
     landing page) still references "more countries coming" now that
     coverage is complete — worth a broader grep next session.

### 2026-09-08 (later still) — Claude (this account) — 5 more Sahel/West African markets
- Continued straight on from the Sierra Leone/Liberia/Mali/Burkina Faso batch
  above (42 markets now). Added **Niger, Gambia, Guinea-Bissau, Chad,
  Mauritania** — user said "add 5 more" with no list, so this session picked
  the Sahel/West Africa neighbors of the countries just added.
- Same 5-agent parallel research process, same verification-honesty
  convention (green/amber/grey `careers_status`), all `source_type` confirmed
  UPPERCASE.
  - Niger: 43 rows (25 DEPT, 10 PRIVATE, 5 NGO, 3 SOE). Flagged another
    hijacked government domain: the Ministry of Health's usual site now
    redirects to gambling spam (3rd such finding this week, after the 2 in
    Sierra Leone — worth a heads-up to someone if there's ever a channel for
    it).
  - Gambia: 38 rows (21 DEPT, 9 PRIVATE, 5 NGO, 3 SOE). Substituted UNICEF for
    Plan International (no Gambia office found) and swapped 3 requested
    private companies for verified alternatives (Trust Bank/GTBank/Julbrew
    had no working sites; used Zenith Bank, FBNBank, Capital Express
    Assurance, Gambia International Airlines, GamSwitch instead).
  - **Guinea-Bissau: 28 rows (18 DEPT, 5 PRIVATE, 5 NGO, 0 SOE, 0 MUNI) —
    genuinely thin, reported honestly rather than padded.** Government runs
    through one portal (`bissaugov.com`) with no per-ministry sites and no
    careers functionality at all; no working SOE website could be found for
    the electricity/water utility, ports authority, or state telecom (only
    Facebook/Wikipedia); MTN Guinea-Bissau no longer exists (rebranded to
    Telecel in 2025) — substituted accordingly.
  - **Chad: 29 rows (20 DEPT, 4 PRIVATE, 5 NGO, 0 SOE)** — 4 ministries and
    all SOE candidates skipped outright (no findable working domain, agent
    declined to guess). ExxonMobil/Esso Chad confirmed exited the country in
    2022 (sold to Savannah Energy) so wasn't listed as a going concern.
  - Mauritania: 44 rows (26 DEPT, 8 PRIVATE, 5 NGO, 5 SOE).
  - Commit `6f14eaa`: `backend/seed/countries/{Niger,Gambia,GuineaBissau,Chad,
    Mauritania}.csv` (182 rows total).
  - Both Niger and Mauritania agents hit the WebSearch 200-call session cap
    partway through, so a handful of private-company/SOE domain guesses in
    those two files are unverified this session (marked `grey_none_verified`
    honestly, not upgraded) — worth a follow-up check before importing.
- Landing page updated per the standing rule: LIVE array (5 new entries,
  `pending: true`), hero badge/footer banner/closing paragraph (37->42
  markets, 16 SADC + 21->26 more), "Employers tracked" stat (3019->3201).
  `tsc --noEmit` clean. Commit `e88f0f8`.
- **Not yet done (same 3 items as the batch before this one, now covering 9
  new countries total):**
  1. **DB import still blocked — needs Lungani's admin login**, same as noted
     below for the Sierra Leone/Liberia/Mali/Burkina Faso batch. All 9 new
     countries (backend/seed/countries/{SierraLeone,Liberia,Mali,BurkinaFaso,
     Niger,Gambia,GuineaBissau,Chad,Mauritania}.csv) need the header row
     prepended and POSTing to `/api/v1/companies/import`.
  2. Verification pass on `grey_none_verified`/`amber_company_route` rows —
     growing backlog, same recurring item as every country batch.
  3. **Push:** now 5 commits ahead of `origin/main` (`fc27ae1`, `c566b12`,
     `9ac85dc`, `6f14eaa`, `e88f0f8`) — still needs Lungani's interactive
     GitHub login via the push `.bat` script.

### 2026-09-08 (later) — Claude (this account) — 4 more West African markets
- Continued from the SADC-completion + Benin/Togo work (33 markets live) noted
  above. Added **Sierra Leone, Liberia, Mali, Burkina Faso** — extends the West
  Africa cluster already live (Nigeria, Ghana, Senegal, Cote d'Ivoire, Guinea,
  Gabon, Benin, Togo). Chosen by this session (no explicit list from Lungani);
  flag if a different set was wanted.
- Researched via 4 parallel agents (WebSearch/WebFetch, real verification, not
  pattern-guessed domains): national government ministries (DEPT), 5 UN/INGO
  country offices each (NGO), 8-10 major private companies (PRIVATE), 3-5
  parastatals (SOE). `careers_status` honestly reflects verification depth
  (green_verified = fetched and confirmed this session; amber_company_route =
  real section found, not pinned; grey_none_verified = best-guess official
  domain). All `source_type` values confirmed UPPERCASE (the casing bug from
  the Lesotho/Botswana session, `aa98f47`/`8b4b7cc`, did not recur).
  - Sierra Leone: 47 rows (28 DEPT, 9 PRIVATE, 5 NGO, 5 SOE). Flagged 2
    compromised/hijacked .gov.sl domains found during research (Ministry of
    Justice's site, and the Basic/Senior Secondary Education jobs sub-page) —
    both now serve gambling-spam content; worth reporting to Sierra Leone's
    government IT if anyone has that channel.
  - Liberia: 35 rows (18 DEPT, 9 PRIVATE, 5 NGO, 3 SOE).
  - Mali: 46 rows (28 DEPT, 10 PRIVATE, 5 NGO, 3 SOE) — French ministry names,
    matching the Togo/Benin/Cote d'Ivoire style.
  - Burkina Faso: 41 rows (24 DEPT, 9 PRIVATE, 5 NGO, 3 SOE) — French ministry
    names; reflects the Jan 2026 transitional-government ministry renaming.
  - Commit `fc27ae1`: `backend/seed/countries/{SierraLeone,Liberia,Mali,
    BurkinaFaso}.csv` (headerless, 10-column format, 169 rows total).
- Landing page updated per the standing rule below: LIVE array (4 new entries,
  `pending: true`), hero badge/footer banner/closing paragraph (33->37 markets,
  16 SADC + 17->21 more), "Employers tracked" stat (2800->3019), "2,800+
  companies" feature line (->3,000+). `tsc --noEmit` clean. Commit `c566b12`.
- **Not yet done:**
  1. **DB import blocked — needs Lungani's admin login.** Tried the admin
     panel at `sospana-sonke.vercel.app/admin` via the built-in browser; it's
     a fresh (logged-out) browser profile on this device, and entering a
     password isn't something this session does. Once Lungani (or a session
     with an active admin browser session) is logged in, import the 4 new
     CSVs the same way the original 10 were done 2026-09-06: prepend the
     header (`company_name,jse_code,careers_url,careers_status,relevance_note,
     active,scraping_status,country,source_type,official_website`) to each
     CSV and POST to `/api/v1/companies/import`.
  2. Verification pass on the `grey_none_verified` / `amber_company_route`
     rows (same outstanding item as every prior country batch — still worth
     an admin URL-tester pass across everything at once eventually).
  3. **Push:** this session's commits (`fc27ae1`, `c566b12`) are local only —
     same non-interactive-push limitation noted below; Lungani needs to run
     the push `.bat` script (or push manually) to get them onto GitHub/
     deployed. Current `origin/main` is 3 commits behind local HEAD.


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

### 2026-09-09 — Claude (this account) — Landing hero redesigned to match brand reference
- User supplied a reference hero-banner image ("Sospana-Sonke — Your Future Is Here")
  and asked to redesign the landing "get started" hero to match it. There is no
  separate `/get-started` route — this refers to the hero section of `frontend/src/app/page.tsx`.
- Rebuilt the hero (commit 49c10e7): "Your Future / Is Here" headline (white + gold),
  tagline highlighting "all 54 African countries", a single primary gold pill
  "Get Started →" CTA (secondary Find jobs / Browse companies / SOE links kept as
  smaller text links), a 4-icon feature row (Find Jobs / Build Skills / Access
  Support / Grow Together), and a new `AfricaMosaic` SVG (continent silhouette
  filled with a flag-colour mosaic pattern + ~12 scattered country-flag badges) in
  place of the old sunrise-skyline art.
- Added `FlagRibbon`: a dark strip closing out the bottom of the hero card, listing
  all 54 `LIVE` countries' flags + names alphabetically (reuses the existing `LIVE`
  array — no new data).
- Moved the Nelson Mandela quote out of the hero into its own small quote-strip
  section directly below, to keep the new hero visually clean like the reference.
- Verified with `npx tsc --noEmit -p tsconfig.json` (clean). Not yet pushed — push
  needs to go through the user's own interactive GitHub login (same limitation as
  every prior session).
- Also confirmed the earlier database-import handoff is unchanged/still pending:
  `sospana-sonke-import-ready.zip` (28 header-ready CSVs) was delivered to the user
  for manual upload via `/admin/companies`; only 26/54 countries are actually in the
  production DB as of this session.
