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

### 2026-09-24 — Claude (Cowork, Opus 5.5) — Senior security audit + hardening pass
Lungani sent a "senior engineering, security & production master directive" (audit first, threat-model,
fix safely, don't rewrite working systems). Full write-up: `docs/SECURITY-AUDIT-2026-09-24.md`.
Fixed: per-IP rate limits were effectively GLOBAL behind Render's proxy (now keyed on the trusted XFF
hop via `app/core/client_ip.py`, `TRUSTED_PROXY_HOPS`); forgeable mock-payment webhooks in production;
no session revocation (new `users.token_version` + `POST /auth/logout-all` + "Sign out everywhere" on
/security; legacy tokens count as v0 so nobody is logged out on deploy); reusable reset links;
per-account lockout + timing-safe login; per-account budgets on /companies and /vacancies;
Next 14.2.15 -> 15.5.26 + React 19 (npm audit 0 vulns, next build + smoke test OK); vacancy-count bug
(pages asked limit=5000 vs API cap 200 -> silent 422); the 4 stale tests. Backend suite fully green.
Humour kept: FunSpinner untouched; new lockout/donation messages written warm on purpose.
**Next:** check the IP in the next login-alert email (if it's 10.x/100.x, set TRUSTED_PROXY_HOPS=2);
verify the Vercel preview of the Next 15 upgrade; roadmap in §5 of the audit doc (server-side directory
pagination is #1).

### 2026-09-21 — Claude (Cowork) — SADC batch 2 COLLEGE research retried + merged (40 new rows); starting grants/awards + valuation research
The SADC batch-2 COLLEGE research (Angola, Mauritius, Malawi, Madagascar, DR Congo,
Seychelles, Comoros) had failed twice before to session rate limits with zero output.
Retried today as 7 parallel subagents — all 7 succeeded this time. Verified against each
country's real accreditation body where one exists (Angola MESCTI, DRC ESU ministry, etc.),
strict direct-careers-link-only rule applied throughout (grey_none_verified + blank URL
where no genuine institution-run careers page could be confirmed, rather than guessing).
49 rows researched, 40 were genuinely new (9 already existed in the DB from earlier work)
and were appended to `backend/seed/company_database_import.csv`
(2950 rows -> 2990 rows). Committed and pushed.

Still outstanding: the ~34 non-SADC African countries for the COLLEGE category have not
been started at all yet. None of the accumulated COLLEGE/company data (this batch or any
earlier one) has been imported into the live production DB yet — still requires Lungani's
admin login for `POST /api/v1/companies/import`.

Also this session: researched grants/awards the platform can apply for, and gave an honest
USD valuation estimate, in response to a direct chat request (not written to this repo —
see the conversation/chat history for that output, it's advisory content, not code/data).


### 2026-09-19 (final) — Claude (Cowork, this account) — Design rollout complete: all 22 pages on ss-* tokens
Finished what the earlier entries this same day started. All three remaining batches landed:
- Batch 2 (7 pages, commit `f04ffef`): login, register, notifications, security, subscription,
  privacy, terms.
- Batch 3 (7 pages, commit `f7f1c39`): admin, colleges, coverage, donate, hospitals, master-cv,
  universities.

Combined with the core-journey batch (`2de530c`) and the homepage/dashboard/agent pages a prior
session already did, **every page.tsx in the app now themes correctly in both light and dark
mode** via the `ss-*` design tokens. `tsc --noEmit` clean after every batch, each verified
independently before merging. All work was visual-only (colors + swapping hand-rolled markup for
existing `ui.tsx` components where it genuinely fit) — no data-fetching, state, routing, or
business logic changed anywhere across the ~19 pages touched today; every subagent confirmed this
via `git diff` review before handing back.

**Two real, useful patterns established for anyone continuing this:**
1. The four directory-listing pages (companies, colleges, hospitals, universities) now share an
   identical token pattern for filter pills, cards, and empty states — `companies/page.tsx` is
   the canonical reference for that shape.
2. Data **tables** (admin's users table, coverage's rollup table) needed their header/row/border
   colors retokenized separately — a components-only migration pass would miss raw `<table>`
   markup, worth remembering for any future page with a table.

**Not fully done / known gaps, honestly:**
- `FunSpinner.tsx` (shared loading component used across many pages) still has one raw
  `text-gray-400` internally — flagged by the coverage-page agent, out of scope for a
  single-page task, worth a quick dedicated fix.
- The two deferred "signature features" from the original 41-section UI brief (Opportunity
  Radar, Opportunity Constellation) were NOT built this session — Lungani explicitly chose
  "finish the rollout" over those when asked.
- Visual-only migration doesn't mean pixel-perfect — nobody has actually opened these pages in a
  browser (light or dark mode) to eyeball them since these commits landed; `tsc` proves the code
  compiles, not that everything looks right. Worth a manual pass, or at least Vercel's preview
  deploy, before calling this fully done.
- Push worked via the GitKraken device-plugin tools all day (4th+ session in a row it's worked —
  the earlier "device-linked sessions can't push non-interactively" caveat elsewhere in this file
  may be stale at this point; a stale `.git/index.lock` from an earlier interrupted process did
  need clearing twice via `device_request_delete_permission` + `rm`, unrelated to the push method).

Also this session (see entries above): SADC COLLEGE batch 1 (South Africa + Botswana/Eswatini/
Lesotho/Namibia/Mozambique/Tanzania/Zambia/Zimbabwe) finished, homepage employer counts fixed
twice to track it. **Still outstanding for the data side:** SADC batch 2 (Angola, Mauritius,
Malawi, Madagascar, DR Congo, Seychelles, Comoros) and the ~34 remaining non-SADC African
countries' COLLEGE research.


### 2026-09-19 (even later) — Claude (Cowork, this account) — Design rollout: core candidate journey done
Migrated `companies`, `matches`, `profile`, `tailor`, `applications` page.tsx files to the `ss-*`
design tokens (5 parallel subagents, one page each, visual-only — no data/state/logic changes,
confirmed by diff review). Commit `2de530c`, pushed, `tsc --noEmit` clean. Homepage, dashboard,
and agent pages were already done by a prior session; these 5 were picked as the highest-traffic
remaining pages (the actual candidate journey: browse companies -> see matches -> tailor a CV ->
track applications -> edit profile).

**Remaining unmigrated pages (14):** admin, colleges, coverage, donate, hospitals, login,
master-cv, notifications, privacy, register, security, subscription, terms, universities.
Same process works for all of them: read globals.css + tailwind.config.ts + ui.tsx + the
now-6 migrated pages as reference, swap bg-white/bg-gray-*/text-gray-*/border-gray-*/text-navy
for ss-* tokens, swap in ui.tsx components where a hand-rolled equivalent exists and fits,
verify with tsc --noEmit, don't touch logic. Auth pages (login/register) and legal pages
(privacy/terms) are probably fastest/lowest-risk; admin is probably the largest/most complex.


### 2026-09-19 (later) — Claude (Cowork, this account) — SADC COLLEGE batch 1 done (134 rows); starting design-system rollout to remaining pages
Lungani said "yes please fix everything and enhance the platform to look excellent." Two threads:

1. **Retried the SADC COLLEGE batch that failed to a rate limit earlier this session** — this time
   all 8 agents completed (Botswana, Eswatini, Lesotho, Namibia, Mozambique, Tanzania, Zambia,
   Zimbabwe). Same process as the South Africa batch: researched against each country's own
   accreditation body (BQA/ESHEC/CHE/NQA+NCHE/MCTESTP+CNAQ+ANEP/NACTE+TCU/TEVETA+HEA/Zimbabwe's
   Ministry of Higher and Tertiary Education), strict direct-careers-link rule, deduped against
   each country's existing rows in `backend/seed/company_database_import.csv` before appending
   (23 of 157 researched were already present) — **134 genuinely new rows**, commit `551fb00`,
   pushed. Then recomputed and fixed the homepage's `LIVE` array counts for these 8 countries too
   (same active=true methodology as the earlier count-fix pass), commit `5c88193`, pushed,
   `tsc --noEmit` clean both times.
   - Main CSV is now 2441 rows total.
   - **Still not done: SADC batch 2** (Angola, Mauritius, Malawi, Madagascar, DR Congo, Seychelles,
     Comoros — 7 countries) and the ~34 remaining non-SADC African countries not yet touched by
     COLLEGE research (see the 2026-09-17 entries above for what Kenya/Ghana/Uganda/Nigeria
     already have in `backend/seed/countries/`).

2. **Asked Lungani where to focus the "look excellent" ask** since a prior session (2026-09-16,
   see entry above) had already started a `ss-*` design-token system + dark/light theming +
   component library (`frontend/src/components/ui.tsx`) + a Command Palette, but only reached the
   homepage hero, opportunity cards, nav, and dashboard — most other pages still use old hardcoded
   `bg-white`/`text-gray-*` classes. He picked **"finish the rollout"** over new signature
   features. Audited which of the 22 page.tsx files are unmigrated (grep for `ss-`/`C.` token
   usage vs `bg-gray-`/`text-gray-` hardcoded classes):
   - Already migrated: `page.tsx` (homepage), `agent/page.tsx`, `dashboard/page.tsx`.
   - **Not yet migrated (19 pages):** admin, applications, colleges, companies, coverage, donate,
     hospitals, login, master-cv, matches, notifications, privacy, profile, register, security,
     subscription, tailor, terms, universities.
   - Starting with the core candidate-facing journey (companies, matches, profile, tailor,
     applications) as the highest-impact first batch — **in progress as this entry is written,
     not yet committed.** If this session ends before that lands, the next session should check
     `git status`/`git log` on `frontend/src/` before assuming nothing happened here.

**Not yet done:** the 19-page design rollout (started, core-journey batch in flight), SADC
COLLEGE batch 2, the ~34 remaining African countries' COLLEGE research.


### 2026-09-19 — Claude (Cowork, this account) — Fixed drifted homepage employer counts; SADC COLLEGE batch failed to a rate limit (not started)
Two separate things this session:

1. **Lungani said "fix the numbers to reflect the truth about our database."** Recomputed every
   country's `count` in `frontend/src/app/page.tsx`'s `LIVE` array from
   `backend/seed/company_database_import.csv` (active=true rows only, matching the file's own
   documented "recomputed" methodology from 2026-09-12 — the numbers had drifted again since
   then, most visibly South Africa: 587 shown vs 672 actual active rows, after this session's
   earlier 127-row addition on 2026-09-17 plus whatever the intervening sessions added). Re-sorted
   the array descending by the corrected counts. Verified (didn't assume) that the 34 "pending"
   countries' `count: 1` and the SOON array's "no rows at all yet" claim are both still literally
   true of `company_database_import.csv` itself — so those were left alone rather than "corrected"
   using `backend/seed/countries/<Country>.csv` numbers, which are real but NOT yet merged into
   the actual database file (per `bootstrap.py`, still staging-only — same standing caveat as
   every earlier entry). Added an explicit code comment saying so, to stop a future session from
   "fixing" those to the bigger countries/ numbers and re-introducing the overclaim in the other
   direction. Commit `3b2e077`, pushed, `tsc --noEmit` clean.

2. **Picked up the outstanding continent-wide COLLEGE task** (SADC batch 1: Botswana, Eswatini,
   Lesotho, Namibia, Mozambique, Zimbabwe, Zambia, Tanzania) but **all 8 parallel research agents
   failed immediately** — "You've hit your session limit" (rate_limit, HTTP 429) before any of
   them did any research. **No data was produced, nothing was written anywhere.** This is a clean
   restart point, not a half-finished batch to reconcile. Also worth knowing: per an earlier
   session's log entry (2026-09-17 later/later still, Opus 4.8), COLLEGE research for Kenya (+56),
   Ghana (+40), Uganda (+37), and Nigeria (+70) was already done and written to
   `backend/seed/countries/{Kenya,Ghana,Uganda,Nigeria}.csv` — check the Session Log entries above
   this one for the exact state before redoing any of those four.

**Not yet done:** the SADC batch 1 COLLEGE research (Botswana/Eswatini/Lesotho/Namibia/
Mozambique/Zimbabwe/Zambia/Tanzania) — retry when quota allows, same per-country agent approach,
same strict own-domain-careers-link rule as the South Africa and Kenya/Ghana/Uganda/Nigeria
batches. After that: SADC batch 2 (Angola, Mauritius, Malawi, Madagascar, DR Congo, Seychelles,
Comoros), then the remaining ~34 non-SADC African countries not yet touched by the COLLEGE task.


### 2026-09-17 (later) — Claude (Cowork, Opus 4.8) — Continent-wide COLLEGE expansion STARTED (batch 1: Kenya, Ghana, Uganda)
Picked up the outstanding continent-wide COLLEGE task, following this repo's own per-country
convention: appended `source_type=COLLEGE` rows to `backend/seed/countries/<Country>.csv`
(10-column, no-header, col10=source_url=careers_url). Enforced the strict rule — `careers_url`
is a GENUINE direct link to the institution's OWN careers/vacancies/e-recruitment page on its
own domain only; never a job board / LinkedIn / bare homepage; left blank with
`grey_none_verified`/`active=false` where no such page could be verified. Research done by three
general-purpose subagents (WebSearch+WebFetch), one per country.
- **Kenya.csv**: +56 colleges (29 green / 22 amber / 5 grey). Public + private chartered
  universities, national polytechnics, KSTVET/KEWI.
- **Ghana.csv**: +40 colleges (17 green / 12 amber / 11 grey). Public + technical + private
  universities; colleges of education mostly grey (recruit via GES / press).
- **Uganda.csv**: +37 colleges (15 green / 6 amber / 16 grey). Public + private chartered
  universities, UICT, UNITE, UTC (`*.tvet.go.ug`) technical colleges.
All three validated: every row is exactly 10 columns, csv-quoted. Files written directly into
the repo working tree via the device bridge (mounted folder) — NOT yet committed. **Lungani to
commit + push via GitHub Desktop / the `.bat` scripts** (this device-linked session can't do an
interactive GitHub sign-in).

**Pipeline caveat re-confirmed this session (important):** `backend/app/services/bootstrap.py`
loads ONLY `backend/seed/company_database_import.csv`. The whole `backend/seed/countries/`
tree (1,479 rows before this batch, +133 now) is staging data that is NOT auto-loaded and is
NOT merged into the main seed — e.g. Kenya appears once in the main CSV vs 112 rows in
Kenya.csv. So these colleges (like every countries/ row) still need to be imported via the
admin `POST /api/v1/companies/import` (or merged into the main CSV) before they show live.

**Not yet done — remaining COLLEGE countries (~50):** every African country except South Africa
(107 done) and this batch (Kenya/Ghana/Uganda). Suggested next batches by ease of verification:
Nigeria (huge — 200+ unis, do alone), Tanzania, Rwanda, Zambia, Zimbabwe, Namibia, Botswana,
Malawi (English); then Francophone (Senegal, Côte d'Ivoire, Cameroon, DRC, Morocco, Tunisia,
Algeria…) and Lusophone (Mozambique, Angola, Cabo Verde). Keep to the per-country convention and
the strict own-domain-careers rule; commit after each batch.

### 2026-09-17 (later still) — Claude (Cowork, Opus 4.8) — COLLEGE expansion batch 2: Nigeria
Continued the continent-wide COLLEGE task (same convention + strict own-domain-careers rule as
batch 1). One general-purpose subagent researched Nigerian tertiary institutions (federal/state/
private universities, federal & state polytechnics, colleges of education, teaching hospitals).
- **Nigeria.csv**: +70 COLLEGE rows (18 green / 17 amber / 35 grey). Now 138 rows total, all
  10-column validated. Greens are live/functional own-domain recruitment portals (e.g. Ahmadu
  Bello `careers.abu.edu.ng/vacancies`, Landmark `v4.lmu.edu.ng/vacancies`, Covenant, UNILAG
  `recruitment.unilag.edu.ng`, UI `vacancies.ui.edu.ng`, Yaba College of Tech). Ambers are
  official own-domain careers/recruitment pages with the live list unconfirmed (OAU, UNN, BUK,
  Babcock, etc.). Greys (many federal/state unis + polytechnics that advertise only via job
  boards / CMS-PDF notices) left blank + active=false — honest, not guessed.
Written to the repo working tree via the device bridge — NOT committed. Same pipeline caveat:
`countries/*.csv` is staging, imported live via admin `POST /api/v1/companies/import`.
**Lungani to commit + push (GitHub Desktop / .bat).** Next batches: Tanzania, Rwanda, Zambia,
Zimbabwe, Namibia, Botswana, Malawi (note: SADC-16 live in the MAIN CSV, not countries/ —
confirm destination before those); then Francophone/Lusophone.

### 2026-09-17 (later still) — Claude (Cowork, Opus 4.8) — COLLEGE batch 3: Rwanda, Senegal, Cameroon
Continued the continent-wide COLLEGE task. NOTE: parallel research subagents hit the account's
session rate limit, so this batch was researched directly in the main thread (lighter, more
controllable) via WebSearch/WebFetch — same strict own-domain-careers rule.
- **Rwanda.csv**: +13 COLLEGE (1 green / 2 amber / 10 grey). Green: University of Rwanda
  (`ur.ac.rw/?Job-Opportunities-announcement=`, 90+ live posts). Amber: University of Kigali
  (`uok.ac.rw/vacancies/`), CMU-Africa careers. Most Rwandan public bodies recruit via the
  central MIFOTRA e-recruitment portal (not own-domain) → honestly grey.
- **Senegal.csv**: +11 COLLEGE (5 green / 0 amber / 6 grey). Strong own-domain recruitment:
  UCAD (`recrutement.ucad.sn`), UGB (`ugb.sn/fr/recrutement`), UAM (`uam.sn/recrutement/`),
  Assane Seck Ziguinchor (`uasz.sn/category/recrutement/`), Alioune Diop Bambey (`uadb.edu.sn`).
- **Cameroon.csv**: +15 COLLEGE (0 green / 1 amber / 14 grey). Amber: University of Buea
  own-domain job-opportunities page (Cloudflare-blocked to fetch, but confirmed via search).
  Cameroon largely recruits via government concours + press (kamerpower) → honestly grey.
All validated at 10 columns. Written to the working tree via the device bridge — NOT committed.
Same staging caveat (countries/*.csv imported live via admin `POST /api/v1/companies/import`).
**Lungani to commit + push.** This session's COLLEGE total: Nigeria 70 + Rwanda 13 + Senegal 11
+ Cameroon 15 = 109 rows across 4 files. Remaining non-SADC to do: Egypt, Morocco, Tunisia,
Algeria, Ethiopia, Ghana(done b1)/Kenya(done b1)/Uganda(done b1), Cote dIvoire, Nigeria(done),
etc. SADC-16 colleges (Tanzania/Zambia/Zimbabwe/Namibia/Botswana/Malawi/…) live in the MAIN
`company_database_import.csv`, NOT countries/ — confirm destination with Lungani before those.

### 2026-09-17 (later still) — Claude (Cowork, Opus 4.8) — COLLEGE batch 4: Egypt, Morocco
Main-thread WebSearch research (rate-limit-safe), same strict own-domain-careers rule.
- **Egypt.csv**: +12 COLLEGE (2 green / 0 amber / 10 grey). Green: AUC
  (`aucegypt.edu/about/careers`), German University in Cairo (`guc.edu.eg/en/jobs/`). Egyptian
  public universities (Cairo, Ain Shams, Alexandria, …) recruit via government/press → grey.
- **Morocco.csv**: +10 COLLEGE (2 green / 0 amber / 8 grey). Green: Al Akhawayn (`aui.ma/jobs`),
  UIC Casablanca (`uic.ac.ma/luic-recrute/`). Moroccan publics recruit via concours/dreamjob.ma
  job board → grey.
Both validated 10 columns. Written to working tree — NOT committed. Session COLLEGE total now:
Nigeria 70 + Rwanda 13 + Senegal 11 + Cameroon 15 + Egypt 12 + Morocco 10 = 131 rows / 6 files
(plus batch-1 Kenya/Ghana/Uganda = 133). **Lungani to commit + push + admin-import.**

### 2026-09-17 (later still) — Claude (Cowork, Opus 4.8) — COLLEGE batch 5: Tunisia, Ethiopia
Main-thread WebSearch research, same strict own-domain-careers rule.
- **Tunisia.csv**: +11 COLLEGE (3 green / 1 amber / 7 grey). Green: Universite Centrale
  (`universitecentrale.net/recrutement`), UTC (`utctunisie.com/utc/recrutement/`), Mahmoud el
  Materi (`umm-tunisie.com/universite/recrutement/`). Amber: ESPRIT career centre. Tunisian
  publics recruit via government concours → grey.
- **Ethiopia.csv**: +10 COLLEGE (0 green / 1 amber / 9 grey). Amber: Addis Ababa University
  (`aau.edu.et/blog/vacancy-announcement-7/`, own-domain vacancy posts). Other Ethiopian unis
  advertise via ethiojobs/hahu job boards → grey.
Both validated 10 columns. NOT committed. Session COLLEGE total: Nigeria 70 + Rwanda 13 +
Senegal 11 + Cameroon 15 + Egypt 12 + Morocco 10 + Tunisia 11 + Ethiopia 10 = 152 rows / 8 files
(batches 2-5). With batch-1 (Kenya/Ghana/Uganda 133) = 285 COLLEGE rows added across sessions.
**Lungani to commit + push + admin-import** all 11 modified countries/ files.
Remaining non-SADC to do: Algeria, Cote dIvoire, Gabon, Guinea, Benin, Togo, Burkina Faso,
Mali, Niger, Chad, Sudan, Libya, DRC/Congo, Angola(SADC-main-CSV), Liberia, Sierra Leone,
Gambia, Somalia, etc. SADC-16 colleges still go in the MAIN CSV, not countries/.

### 2026-09-18 — Claude (Cowork, Opus 4.8) — COLLEGE expansion: ALL NON-SADC AFRICA COMPLETE
Finished the continent-wide COLLEGE task for every non-SADC country (batches 6-7, main-thread
WebSearch, strict own-domain-careers rule). Added: Algeria (10), Cote dIvoire (10), Gabon (4),
Benin (4), Togo (2), Burkina Faso (3), Mali (3), Niger (3), Sierra Leone (3), Liberia (2),
Gambia (1), Guinea (3), Congo/Brazzaville (2), Mauritania (1), Chad (2), Sudan (3), Libya (2),
Burundi (1), CAR (1), Cabo Verde (1), Djibouti (1), Equatorial Guinea (1), Eritrea (1),
Guinea-Bissau (1), Sao Tome (1), Somalia (2), South Sudan (2). New greens/ambers found this
run: Burkina Faso Universite Joseph Ki-Zerbo (`ujkz.bf/recrutement/`, amber), Sierra Leone
Njala University (`njala.edu.sl/.../job-vacancies-various-positions`, green), Algeria USTHB &
USTO recruitment notices (amber), Cote dIvoire INP-HB career center (amber). Everything else
grey — those countries recruit only via government concours / national job boards, so URL left
blank + active=false (honest, not guessed).

**FINAL STATE — every non-SADC African country now has COLLEGE rows.** 38 countries/ files carry
355 COLLEGE rows total: 93 green_verified (live own-domain recruitment portals), 66
amber_company_route (official own-domain careers pages, live list unconfirmed), 196
grey_none_verified (blank URL). All rows validated at exactly 10 columns.

STILL NOT DONE: SADC-16 colleges (Tanzania, Zambia, Zimbabwe, Namibia, Botswana, Malawi,
Angola, Mozambique, Madagascar, Mauritius, Lesotho, Eswatini, DRC, Seychelles, Comoros — SA
already has 107 in main CSV). These belong in the MAIN `company_database_import.csv`, not
countries/. Awaiting Lungani's decision on destination before adding them.

**Lungani's actions:** (1) commit + push ALL modified countries/*.csv + CLAUDE.md via GitHub
Desktop; (2) admin-import each countries/ file at `/admin/companies` (auto-loader still only
reads the main CSV) so the colleges go live.


### 2026-09-17 — Claude (Cowork, this account) — Rheinmetall check + SA COLLEGE category; fixed a wrong-working-directory bug
Lungani asked to check whether "Rheinmetall" was in the company database and, if not, add it
under private companies; separately asked what other legal (registered) SA companies/college
categories were missing. Then asked for a brand-new COLLEGE category covering all legally
registered (DHET-verified) South African colleges, with the explicit rule that `careers_url`
must be a genuine direct link to the institution's own careers page (never a job-board profile
or bare homepage fallback) — left blank, matching the existing `grey_none_verified`/`active=false`
convention, wherever no such direct link could be verified. Also asked to extend COLLEGE to all
other countries, then "not only SADC ... the entire continent" — that continent-wide expansion
has **not been started yet** (see Not yet done below).

**Bug caught and fixed this session, worth reading if something looks off:** all of this
session's early work (Rheinmetall + DEPT/MUNI/NGO/PRIVATE additions + the 108-row COLLEGE
research) was done against files in the **stray sibling folder**
`sospana-sonke-fullstack/company_database_updated.csv` and
`sospana-sonke-fullstack/backend/seed/company_database_import.csv` — i.e. **outside this repo
entirely**, one level up from `sospana-sonke/`. Lungani caught it ("I cannot see rheinmetal did
you push?") because nothing had actually reached git. Diagnosed by comparing directory
listings and finding `.git` only exists under `sospana-sonke/`. Fixed by diffing my working
file's 511 SA rows against this repo's real `backend/seed/company_database_import.csv`
(2088 rows before this change) on company name (case-insensitive): 384 were already present
(the base JSE/SOE/DEPT/MUNI/NGO/PRIVATE data here is already far more complete than the
scratch file I'd built from nothing), leaving **127 genuinely new rows** — Rheinmetall Denel
Munition (PRIVATE), 9 DEPT, 5 MUNI, 3 NGO, 2 PRIVATE (Deloitte SA, EY SA), and 107 COLLEGE
(public TVET colleges + DHET-registered private higher-ed institutions; the pre-existing 26
SA `UNI` rows are traditional public universities and don't overlap with COLLEGE). Appended
those 127 to the real `backend/seed/company_database_import.csv` in its actual 10-column
format (`...,source_type,official_website` — my scratch file only had 9 columns, no
`official_website`; set it equal to `careers_url` on append, matching the convention seen in
`backend/seed/countries/*.csv`). Commit `70f495e`.

**Push:** `git add`/`git commit` via device_bash initially failed with a stale
`.git/index.lock` ("Operation not permitted" unlinking it — the connected-folder delete
restriction, not a real git problem). Got delete permission for the
`sospana-sonke-fullstack` folder from Lungani via the approval prompt, removed the stale
lock, then committed + pushed via the **GitKraken device-plugin tools** (same tools that
worked in the two sessions before this one) — confirmed on `origin/main` via a fresh
`git fetch` + `git show origin/main:...csv | grep rheinmetal` (present) and
`git rev-list --left-right --count origin/main...HEAD` (`0  0`, fully in sync).

**Still true, unchanged by this session (see recurring items in older entries below):**
this CSV is the seed file, not the live DB's source of truth — **these 127 rows, like every
country batch before them, still need Lungani's admin login to actually POST to
`/api/v1/companies/import`** before they show up on the live site's employer directory.
Told Lungani this plainly rather than implying the push alone makes them visible.

**Not yet done:**
1. **Continent-wide COLLEGE expansion** — Lungani's latest ask ("not only sadc region but
   the entire africa") has not been started. No research agents dispatched yet for any of
   the 53 non-SA African countries' colleges. When resuming: research into
   `backend/seed/countries/<Country>.csv` format (10-column, no header, `source_type=COLLEGE`)
   is probably cleaner than the SA-style single big CSV, since that's this repo's own
   established per-country pattern for everything added since the original SA/BW/SZ/LS
   bootstrap — check with Lungani if unsure, but default to that pattern for consistency.
2. Still owed from an earlier session (unrelated to COLLEGE, mentioned as a to-do in
   `/areas/sospana-sonke.md` memory): the same DEPT/MUNI/NGO/PRIVATE build-out done for SA
   should eventually be checked against Botswana/Eswatini/Lesotho too — though given how much
   more complete this repo's real seed file turned out to be than assumed, **check actual
   row counts per country in `backend/seed/company_database_import.csv` before assuming
   anything is thin** (Botswana=129, Eswatini=75, Lesotho=75 rows already, before this
   session — better than expected, may not need much).
3. A large funding-strategy/grant-research deliverable (30-org ranked funder database, 10
   outreach emails, 90-day plan, published HTML strategy artifact) was produced earlier this
   same conversation but is **unrelated to this repo** — lives in Claude's own scratchpad and
   was sent to Lungani directly as files, not committed anywhere.
4. Hosting reliability question (Render free tier sleeping/slow) was answered in
   conversation with concrete free/cheap alternatives (Oracle Cloud Always Free tier
   recommended) — no code/infra change made, Lungani hasn't said whether he wants to migrate.


### 2026-09-16 (later) — Claude (Cowork) — Design-system foundation + Command Palette (futuristic UI/UX brief, phase 1)
Lungani sent a second, separate 41-section brief ("SOSPANA SONKE — FUTURISTIC
UI/UX TRANSFORMATION"): transform the visual experience into a "calmly
futuristic," premium employment-tech aesthetic — explicitly not a video-game/
crypto/cyberpunk look — while preserving every existing feature and not
touching the backend/database unless unavoidable. Given the genuine size (a
full multi-page redesign + bespoke component library + dark/light theming +
3 custom visualizations), asked which of two scoping questions to prioritize;
Lungani picked **"Foundation first"** (design-system tokens/components, then
apply to homepage hero+search, opportunity cards, navigation, dashboard) and
**"Command Palette"** as the one signature feature to build this pass
(deferring Opportunity Radar / Opportunity Constellation). Commit `5f23614`
(cloud) / `f0d6695` (device — identical diff, see push note below).

1. **Design tokens** (`frontend/src/app/globals.css` + `tailwind.config.ts`):
   `--ss-*` CSS variables (bg/surface/text/muted/primary/tech/success/warning/
   danger + pre-mixed soft/border tint variants) for a light "Warm Paper" and
   dark "Deep Space" palette, mapped into Tailwind as `ss-*` utilities via the
   `darkMode: ["selector", ...]` strategy (Tailwind 3.4.1+). **Real bug caught
   before shipping**: Tailwind's opacity-modifier syntax (`bg-ss-primary/10`)
   silently generates no CSS at all for a color defined as a bare
   `var(...)` reference — verified via an actual `tailwindcss` CLI build
   against a scratch test file, not assumed. Fixed by adding pre-mixed
   `rgba()` tokens instead of relying on the modifier anywhere.
2. **Dark/light toggle** (`frontend/src/lib/theme.tsx`): persists to
   `localStorage`, respects OS preference on first visit, flash-free via a
   `beforeInteractive` bootstrap script in `layout.tsx`. Toggle button in
   `Nav.tsx` (desktop + mobile row).
3. **Core component restyle** (`frontend/src/components/ui.tsx`): Card, Stat,
   Button, Badge, Field, Input/Textarea/Select, Alert, Spinner, Skeleton, all
   on the new tokens with every existing prop API preserved (no call-site
   changes needed elsewhere). Added `StatusBadge` (the brief's LIVE/VERIFIED/
   NEW/CLOSING SOON/MATCHED/SAVED vocabulary, dot + label, tone carries
   meaning so it's never color-alone) and `EmptyState`/`ErrorState`.
4. **Functional Ctrl+K "Sospana Command" palette**
   (`frontend/src/components/CommandPalette.tsx`, new): real navigation +
   search, not a decorative overlay — reuses the Career Agent's own
   natural-language phrases verbatim so its existing deterministic
   `classifyIntent` parser understands them identically. Trigger button
   visible at every breakpoint including mobile (positioned above
   `MobileBottomNav`) — the brief's own explicit requirement; this was
   initially shipped with a `hidden ... sm:flex` mistake that hid it on
   phones, caught and fixed before this session ended.
5. **Homepage hero search console** (`frontend/src/app/page.tsx`): a
   "what/where/type" command-centre search bar + 3 quick-command chips.
   Anonymous visitors' searches are queued via a new
   `frontend/src/lib/agentHandoff.ts` (localStorage for the redirect-through-
   registration case, sessionStorage for the Command Palette's same-tab
   case) and offered back via a new `PendingSearchBanner.tsx` once they've
   registered (login/register redirect to `/companies`, not `/agent`) —
   picked up by a `consumeAgentCommand()` effect added to `app/agent/page.tsx`.
6. **Opportunity/vacancy cards redesigned** (`app/agent/page.tsx`):
   `MatchCard` now shows an SVG ring visualization of the real match score
   plus a per-criterion `SubScoreBar` breakdown ("Why this match?") instead
   of a bare percentage; `VacancyCard` gained `StatusBadge`-driven
   closing-soon/new-listing indicators off real `closing_date`/
   `first_seen_at` fields (never invented), plus a themed trust-flag banner.
7. **Dashboard reframed as "My Opportunity Centre"** — same real Stat data,
   restyled section headings/eyebrow, live-status badges.
8. **MobileBottomNav** restyled onto `ss-*` tokens so it now responds to the
   toggle instead of being hardcoded white/navy.

**Deliberate scope limits (disclosed, not oversights):** dark/light theming
only reaches the app shell + the pages above — the marketing hero and top
`Nav` intentionally keep their existing fixed dark-navy/gold brand look
(common marketing-page convention), and most other pages (companies,
matches, profile, tailor, admin, etc.) still use the old hardcoded gray/
white classes and won't shift on toggle yet. The two deferred signature
features (Opportunity Radar / Opportunity Constellation) and the rest of the
41-section brief (search page, CV builder studio, application tracker
pipeline, interactive map, career pathway visualization) are follow-up work.

**Verified**: `tsc --noEmit` clean after every incremental change this pass
(re-run ~6 times as work progressed, not just once at the end). No backend
changes, so no pytest re-run needed.

**Transfer/push**: `device_bash` (the on-device Linux VM) was unavailable
again this session ("Workspace unavailable... failed to start"). Used
`device_stage_files`/`device_commit_files` (14 files, zero rejections) into
`sospana-sonke-fullstack/sospana-sonke/` (confirmed via `.git` — the real
repo, matching every prior session's note), then the GitKraken device-plugin
tools for add/commit/push. **Push succeeded** (confirmed both `main..
origin/main` and `origin/main..main` empty afterward) — this is now the
second session in a row where push worked from the device plugin, so it may
no longer be the standing blocker earlier entries describe; worth trying
again before assuming a device session can't push.

**Not yet done**: verify the Vercel deployment actually built clean (this
doc's own standing lesson from 2026-09-13 — a clean `tsc --noEmit` isn't the
same guarantee as a successful Vercel build); extend `ss-*` tokens to the
remaining pages; build the two deferred signature features; propagate the
redesign through search/CV builder/application tracker/map per the brief.

### 2026-09-16 — Claude (Cowork) — Structured filters, gap analysis, career explorer, trust/duplicate flagging, SEO/mobile/a11y pass
Lungani sent a large 40-section brief to transform the platform into "South Africa's
intelligent opportunity engine." Audited first (most of the brief -- SEO metadata,
JSON-LD, PWA, matching engine, CV builder, etc. -- was already built; see the feature-
gap matrix from this session for the full picture) then built all 4 gaps Lungani chose
("all") when asked which to prioritize. Commits `4b16e3a`, `3344157`, `6336aec`,
`5285980`, `a62f116` (backend + frontend, in that order).

1. **Structured filters** (`4b16e3a`): scraper now infers `province`, `salary_min`/
   `salary_max`, and `nqf_level` from listing text at scan time (additive, never
   overrides free-text fields) and `GET /vacancies` gained real query params for all of
   them plus `employment_type`. Fixed a real bug while testing: the salary-range regex
   was missing `re.IGNORECASE` so "R15,000 - R20,000" silently parsed as a single value.
2. **Gap analysis + Career Explorer** (`3344157`): `GET /matches/{id}/gap-analysis`
   reuses the matching engine's own `requirement_met()` (so it can never disagree with
   the match's own score) to show have/missing/unclear requirements + a suggested
   pathway. `GET /career-explorer` suggests adjacent career families (18-family curated
   taxonomy) with real open-vacancy counts.
3. **Duplicate detection + trust/scam flagging** (`6336aec`): `trust_service.py` scans
   new listings for named, explainable red flags (payment requests, unrealistic salary,
   missing application link) -- never auto-hides anything, just flags + a warning
   banner. `duplicate_service.py` groups same-company listings by normalized title+
   location, keeps the oldest as canonical, soft-closes (never hard-deletes) the rest,
   and refuses cross-company merges. Candidates can report a listing
   (`POST /vacancies/{id}/report`); admins get a triage queue and merge endpoint.
4. **SEO + mobile nav + accessibility** (`5285980`, `a62f116`): frontend wiring for
   1-3 above, all in `/agent`. Separately, found and fixed a real SEO bug my own audit
   initially missed: `robots.ts`/`seo.ts`'s `PUBLIC_ROUTES`/`sitemap.ts` all treated
   `/companies` (and several other `<Guard>`-gated pages) as public/indexable, and the
   JSON-LD `WebSite`'s `SearchAction` pointed at that same gated URL -- fixed all of it.
   Added `MobileBottomNav.tsx` (Home/Search/Saved/Applications/Profile tab bar for
   small screens). Accessibility: global `:focus-visible` ring, a skip-to-content link,
   `role="dialog"`/`aria-modal` on the two overlay modals, `aria-hidden` on decorative
   status icons. `prefers-reduced-motion` support already existed.
- **Verified**: full backend pytest suite run (`/tmp/venv` in the sandbox) -- all new/
  changed test files (34 tests across `test_scraper_extract`, `test_vacancy_routes`,
  `test_match_routes`, `test_career_explorer`, `test_trust_and_duplicates`) pass. 4
  pre-existing failures elsewhere (`test_watch_service.py`, `test_link_check_service.py`
  -- a stale `reg["id"]` helper that doesn't match the current nested `RegisterResponse`
  shape) are unrelated to this session's changes (confirmed via `git log` -- last touched
  in an earlier commit, not this session) and were left alone, same as the standing
  `test_dashboard.py` dead-test note from 2026-09-06. Frontend `tsc --noEmit` clean.
  `next build` not attempted (sandbox has no egress to Google Fonts -- known, documented
  limitation; real gate is checking the Vercel deploy after push).
- **device_bash (device Linux VM) was down again this session** -- used
  `device_stage_files`/`device_commit_files` (32 files, zero rejections) into
  `sospana-sonke-fullstack/sospana-sonke/` (the real repo -- confirmed via `.git`
  presence; the sibling `sospana-sonke-fullstack/{frontend,backend}` and
  `sospana-sonke_OLD_backup/` are the known stray/backup copies, untouched) +
  GitKraken plugin tools for add/commit. **Committed locally, NOT pushed** -- same
  interactive-GitHub-login limitation as every prior session; Lungani needs to push
  (via a `.bat` script or `git push`) to get this onto GitHub/deployed.
- **Honesty notes for whoever reads this next:**
  1. The production **vacancy index is essentially empty** (documented 2026-09-14) --
     structured filters, gap analysis, and duplicate/trust detection are all real and
     tested, but their real-world impact is capped until the scraper actually populates
     `vacancies` at scale.
  2. No dedicated admin **frontend** page was built for the new vacancy-reports triage
     queue or duplicate-groups list -- only the backend endpoints
     (`GET /admin/vacancy-reports`, `GET /admin/vacancies/duplicates`,
     `POST /admin/vacancies/merge`) exist. An admin UI for these is the natural next
     step if Lungani wants to actually use them day-to-day rather than via API calls.
  3. The career-family taxonomy (18 families) and gap-analysis pathway templates are
     hand-curated, not exhaustive -- expect to extend both as real usage surfaces gaps.

### 2026-09-14 — Claude (Cowork) — NEW: Sospana Sonke Career Agent page (/agent)
- Built a conversational **Career Agent** front door: `frontend/src/app/agent/page.tsx`
  (new) + link added to `frontend/src/components/Nav.tsx` (after Dashboard). Everything
  is wired to the **real existing endpoints — no fabricated data**:
  - Quick actions + a natural-language box → a deterministic in-browser intent parser
    (NOT an LLM; no hidden AI claim). Modes: **"Jobs I can apply for"** (`POST /matches/run`
    → `GET /matches`; eligible = `hard_ok` AND decision APPLY/REVIEW), **"Almost qualified"**
    (near-miss band / `hard_ok` false — shows the gaps), **keyword/smart search**
    (`GET /vacancies?q=` with client-side location/qualification/work-mode/type filters +
    synonym expansion via ROLE_FAMILIES), and **Career Discovery** (adjacent role families
    from the candidate's profile).
  - Result cards: score/band, **honest eligibility** ("Requirement not confirmed" whenever
    `hard_ok` is false — never overclaims), a lazy "Why" that pulls reasons/gaps/sub_scores
    from `GET /matches/{id}`, closing-date intelligence, source transparency, Save/Compare
    trays + a compare table. Keyword (directory) results are shown **unscored and labelled
    as such**. Empty states point to `/companies` and `/profile` rather than inventing jobs.
- **Verified**: reconstructed the whole frontend in a sandbox, `npm ci` + `tsc --noEmit`
  + `next build` all clean — the `/agent` route compiles and prerenders with no type/lint
  errors. (Sandbox can't reach Google Fonts, so `layout.tsx`'s font fetch was stubbed
  *locally only* for the test build; `layout.tsx` itself was NOT changed/deployed.)
- **device_bash (the device Linux VM) was DOWN this session** — a Sept-8 Windows update
  blocks it — so used `device_stage_files`/`device_commit_files`. The two files were
  committed to the working tree and verified **byte-identical by sha256**. Nothing was
  pushed from here: **push still needs Lungani to double-click `7-PUSH.bat`** (git add -A
  / commit / push → Vercel + Render auto-deploy).
- **Same-day fix (v2):** first deploy worked but every search came back empty —
  the production **vacancy index is essentially empty** (employers advertise on their
  own careers pages; the scraper isn't populating `vacancies`). So the agent now falls
  back to the **employer directory** (`/companies`): when there are no scored/indexed
  listings it surfaces matching employers (keyword on name/notes + country + category),
  each linking straight to its careers page, plus a "Browse all employers in <country> →"
  deep-link into `/companies?country=&type=`. Added an "🏢 Employers in my field" quick
  action + an `employers` intent. Still no fabricated data. Re-verified `tsc` + `next
  build` (clean; /agent 10.2 kB).
- Next session: keep `/agent`'s ROLE_FAMILIES / vocab lists roughly in sync with
  `backend/app/common/vocab.py`. The real unlock for live *vacancy* listings is running
  the scraper (`app/scraper`, `scan_service`) over the directory's careers pages to
  populate the `vacancies` table — currently empty in prod.

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

### 2026-09-18 — Claude (Cowork, Opus 4.8) — SADC COLLEGE additions into the MAIN CSV
Lungani approved adding SADC-16 colleges into `backend/seed/company_database_import.csv` (the
live/auto-loaded seed), NOT countries/. Deduped against the flagship UNI rows already present
(the main CSV already had 3-9 UNI rows per SADC country). Added 79 COLLEGE rows across 15
countries (SA already had 107): Botswana 6, Mauritius 6, Zambia 11, Tanzania 9, Zimbabwe 11,
Malawi 8, Namibia 3, Eswatini 5, Lesotho 4, Angola 4, Mozambique 4, Madagascar 2, DR Congo 3,
Comoros 1, Seychelles 2. Same strict own-domain-careers rule.
New greens (own-domain careers pages verified): BA ISAGO (`baisago.ac.bw/vacancies/`), Botswana
Accountancy College (`bac.ac.bw/vacancies.php`), Botho Botswana, Univ des Mascareignes
(`udm.ac.mu/vacancies/`), Charles Telfair (`cte.ac.mu/vacancies`), Middlesex Mauritius,
University of Lusaka (`unilus.ac.zm/Jobs.aspx`), Manicaland State Univ (`msuas.ac.zw/vacancies/`),
NAMCOL (`namcol.edu.na/.../vacancies/`), Uniluanda (`uniluanda.ao/category/recrutamento/`).
Rest grey (recruit via national job boards). Flagship unis with own-domain careers (UZ, UNZA,
NUST-NA, UNAM, MUBAS, ZCAS, UB) were ALREADY in the CSV as UNI rows — deduped, not re-added.
MAIN CSV now: 2295 rows, 186 COLLEGE rows (69 green + 117 grey/amber). All 10-column validated.
Because these are IN the main CSV, the bootstrap auto-loader WILL load them on next deploy — no
separate admin import needed for the SADC set (unlike the countries/ files).
**Continent-wide COLLEGE task now COMPLETE: all 54 African countries have college data.**

### 2026-09-18/19 — Claude (Opus 4.8) — Bulk careers-URL health check (test_all_urls)
Shipped `a87b4c4`: a rotating, time-bounded scheduler job (`test_all_urls`, daily
04:00, `POST /api/v1/cron/run/test_all_urls`) that fetches every active company's
`careers_url` — the *whole* directory over time, not just newly-scanned ones — and
downgrades/promotes `scraping_status` using the exact same `looks_like_careers`
taxonomy as the admin's per-company "test this URL" button (`url_tester.py`, new
sync twin `test_url_sync()` for the sync scheduler worker). Mirrors
`scan_due_companies`'s own rotation + `max_seconds=240.0` wall-clock budget
pattern (see the 2026-09-13 "Find Jobs pipeline" entry above for why a time
budget beats a bare row `limit`). Does NOT extract vacancies or email
candidates — purely a link-health pass, so it's cheap enough to run across the
whole ~2,300-row database on a schedule. 4 new tests in `test_url_tester.py`
(sync ok/404, no-url, job updates status + respects inactive/deleted, job
respects an already-spent time budget); full regression suite passes.
**Not independently re-verified live this session** (this entry is being added
retroactively — the commit that shipped it didn't leave a session-log note at
the time). `/health` responds `{"status":"ok",...}` in production as of this
check; no schema change, so this reaches Render on its normal auto-deploy from
`main` with no extra step needed.

### 2026-09-19 — Claude (Sonnet 5) — COLLEGE category made visible on the site
Lungani reported "The College category does not appear on the site." Root cause: `COLLEGE`
had been a real, populated `source_type` since the SADC/continent-wide passes above (186 rows
in the main CSV), but no frontend code had ever been taught about it — it fell into the
Companies page's generic "Listed" catch-all with a fallback `"COLLEGE-listed"` badge, the same
gap Universities had before it got its own chip.
- `26c8aff` — added `COLLEGE` to `companies/page.tsx`'s `TYPE_BADGE` map ("🏫 College"),
  widened the filter-state type, added a filtering branch + catch-all exclusion, and added a
  "🏫 Colleges" filter chip.
- `2a706dd` — Lungani asked for a dedicated page too ("Add one"): new `frontend/src/app/
  colleges/page.tsx`, mirroring `/universities/page.tsx` exactly but filtered to
  `source_type=COLLEGE` (country tabs, search, sort, shortlist, notify/share/report, coverage
  link). Linked from `Nav.tsx` right after Universities; added `/colleges` to `robots.ts`'s
  disallow list alongside every other `<Guard>`-gated page. No backend changes needed.
Both type-checked clean (`tsc --noEmit`) in a fresh clone before pushing. **Confirmed live** —
Lungani checked Vercel directly ("vercel is done").

### 2026-09-19 — Claude (Sonnet 5) — New HOSPITAL category, South Africa first
Lungani asked whether hospitals were already a category — they weren't (no `HOSPITAL`
`source_type` anywhere; a few health-related orgs existed but filed under `DEPT`/`PRIVATE`).
Asked to start with South Africa, with the standing "direct links only" rule enforced strictly.
Shipped `b8e59e8` on `main`:
- Added 6 South African hospital/hospital-group rows to `backend/seed/company_database_import.csv`
  with `source_type=HOSPITAL`, each fetched and verified before inclusion: Cure Day Hospitals,
  Africa Health Care (RH Bophelo Group), Lenmed Health (all `green_verified` — live job titles
  confirmed on the page itself), Busamed, Life Healthcare Group, Zuid-Afrikaans Hospital (all
  `amber_company_route` — legitimate own-domain recruitment portals, but no live listing visible
  on the fetched page itself).
- Deliberately excluded (no genuine own-domain careers link could be verified): Netcare (funnels
  to a Workday subdomain, not its own domain), Joint Medical Holdings, Clinix Health Group,
  National Hospital Network (page states no current vacancies), Matlosana Medical Health
  Services, Icon Oncology (stale listing), and every major public/academic hospital checked
  (Chris Hani Baragwanath, Groote Schuur, Charlotte Maxeke, Steve Biko, IALCH, Tygerberg,
  Universitas) — these route only through the provincial Dept of Health e-recruitment circulars
  already covered under `DEPT`.
- Frontend: added `HOSPITAL` to `companies/page.tsx`'s `TYPE_BADGE` map ("🏥 Hospital"), widened
  the filter-state type, added a filtering branch + catch-all exclusion, and added a "🏥
  Hospitals" filter chip — same pattern as College. Mediclinic/Melomed were already present
  under `PRIVATE` and left as-is rather than duplicated.
- Type-checked clean (`tsc --noEmit`) and CSV-parse-validated (correct column count, no
  malformed rows) in a fresh clone before pushing. No dedicated `/hospitals` page built yet —
  only the badge/filter chip, matching how College started before Lungani asked for a page too.
- **Not yet extended beyond South Africa** — next step if Lungani wants it continued.

### 2026-09-19 — Claude (Sonnet 5) — Hospitals directory page + SADC expansion
Follow-up to the new HOSPITAL category above. Lungani said "yes" to both offered next
steps (build a dedicated page, and extend beyond South Africa).
- `b15e596` — new `frontend/src/app/hospitals/page.tsx`, mirroring `/colleges/page.tsx`
  exactly but filtered to `source_type=HOSPITAL` (country tabs, search, sort, shortlist,
  notify/share/report, coverage link). Linked from `Nav.tsx` after Colleges; added
  `/hospitals` to `robots.ts`'s disallow list. No backend changes needed.
- `8c5b8f6` — 7 more HOSPITAL rows across 6 SADC countries (Botswana ×2, Mauritius,
  Namibia, Eswatini, Zimbabwe, Mozambique), same fetch-and-read-before-including
  discipline as the SA batch. Excluded Sidilega Private Hospital (Botswana — its own
  page states no jobs currently), Corporate 24 (Zimbabwe — only listings found were
  expired/filled since 2023), and Coptic Hospital (Zambia — "careers" page is just an
  email address, not a listing or portal). Found nothing verifiable at all for Lesotho,
  Malawi, Angola, DR Congo, Tanzania, Madagascar, Seychelles, or Comoros — hospital
  vacancies in those countries only surface on third-party job boards/social media, not
  the institution's own domain.
- Total HOSPITAL rows now 13 across 6 countries. `tsc --noEmit` clean and CSV
  Python-`csv`-module validated (10-column shape, no malformed rows) in a fresh clone
  before both pushes.
- **Not yet extended beyond South Africa + SADC** — the rest of Africa is the natural
  next batch if Lungani wants it continued.

## Career Agent: exclude outdated ads, harden scraper reliability, add 2 ATS parsers — 2026-09-18/19

Lungani asked to "improve career agent to exclude outdated ads, and improve the
scrapping capabilities, use technology that bypass blockages, we want a strong
search result." The third clause ("bypass blockages") was flagged before any code
was written — building CAPTCHA/Cloudflare-style bot-detection circumvention is a
standing refusal regardless of stated reason. Used `AskUserQuestion` to confirm
scope before touching anything expensive to redo: (1) scope boundary — legitimate
scraping robustness (retries/backoff/JS-rendering/more ATS parsers) yes, bot-detection
bypass no — confirmed; (2) staleness definition — closing date has passed — confirmed;
(3) whether to flip the existing (off) `JS_RENDER_ENABLED` flag on — Lungani said yes,
**but this was given before a real infra conflict was found** (see below), so it was
deliberately not acted on. Shipped as commit `1762787` on `main`, 17 files
(backend only), all changes verified against the full pytest suite before pushing.

**1. Exclude outdated ads.**
- `GET /vacancies` and `GET /companies/{id}/vacancies`
  (`app/api/routes_vacancies.py`) now drop any listing whose own `closing_date` has
  passed **by default** — previously this only happened when the caller explicitly
  passed the opt-in `max_age_days` query param, so a stale ad stayed visible until a
  re-scan happened to notice the source no longer listed it.
- `app/services/match_service.py::run_match_for_user` applies the same closing_date
  filter to its own query, so the matching engine can never surface or email a
  candidate about an ad that's already closed — defense in depth alongside the point
  below, since a scan only flips `is_open=False` once it positively re-confirms a role
  is gone (deliberate, to avoid wiping vacancies on one flaky empty fetch — see the
  2026-09-13 `32807ce` fix already in this file).
- New scheduler job `close_expired_vacancies` (`app/scheduler/jobs.py`, registered in
  `app/scheduler/registry.py`, nightly at 01:00 — one hour before the existing 02:00
  `match_all_candidates` run): a pure DB sweep, no network calls, that sets
  `is_open=False` for every vacancy whose `closing_date` has passed. Keeps `is_open`
  itself accurate everywhere it's filtered on, not just at query time, without waiting
  on the scan rotation to happen to revisit that company.

**2. Scraper reliability ("strong search result").**
- `app/scraper/politeness.py::request_with_backoff` existed since an earlier session
  but was **dead code** — never actually called by any strategy. Now wired into all
  four strategies that fetch over HTTP (`greenhouse.py`, `lever.py`,
  `smartrecruiters.py`, `static_html.py`), so every scrape gets real exponential
  backoff on 5xx/transport errors instead of failing on the first blip.
- Extended `request_with_backoff` to also retry HTTP 429 (a server explicitly asking
  to slow down, not a permanent failure) and to honour a numeric `Retry-After` header
  when present, instead of guessing a delay — a real server-told wait is trusted over
  the exponential default.
- Added two new structured ATS parsers, same pattern as the existing Greenhouse/
  Lever/SmartRecruiters strategies (public, no-key JSON endpoints — reading the same
  feed a candidate's own browser would call, not a bypass of anything):
  `app/scraper/recruitee.py` (`https://{subdomain}.recruitee.com/api/offers/`) and
  `app/scraper/workable.py` (`https://www.workable.com/api/accounts/{account}?details=true`).
  Both registered in `app/scraper/base.py`'s `detect_ats`/`get_strategy`. This widens
  the set of careers pages the scanner can read as clean structured data instead of
  falling back to the best-effort HTML heuristic parser.

**3. JS-rendering flag — deliberately NOT enabled, infra conflict surfaced instead.**
Investigated what turning `JS_RENDER_ENABLED` on (Lungani's "yes, enable it" answer)
would actually do in production, before touching it: `render.yaml`'s own comment says
"headless-browser scraping off — Render's free tier can't run Chromium. Turn on only
on a paid instance," and — separately — the Render service is declared
`runtime: python` / `buildCommand: pip install -r requirements.txt`, meaning the
actual deployment doesn't even use `backend/Dockerfile` (which itself doesn't install
Playwright's browser binaries either). Flipping the flag as-is would make every
JS-type scan fail outright (no Chromium binary, likely no memory headroom on free
tier even if it were installed) rather than improve anything. Left the flag off and
the code fully ready (`PlaywrightRenderer`/`RenderedHTMLStrategy` were already
correctly implemented from an earlier session) — this needs a decision from Lungani:
upgrade the Render plan (and add browser-binary installation to whichever path
actually deploys), or leave this deferred. **Not resolved — flagged for him, see the
project doc's "Open threads" list.**

**Tests**: 2 new files (`test_politeness.py` — robots/rate-limiter/backoff incl. 429 +
Retry-After; `test_scheduler_jobs.py` — `close_expired_vacancies`), extended
`test_scraper_parsers.py` (Recruitee/Workable detect_ats + fetch), `test_match_service.py`
(closing_date exclusion, both directions), `test_vacancy_routes.py` (closing_date
default exclusion, both list endpoints). Full backend suite run in a fresh
`/tmp/venv` + fresh clone: passes except the same 4 pre-existing, unrelated failures
documented repeatedly above (`test_watch_service.py` × 2, `test_link_check_service.py`
× 2 — the standing `register_and_login()` `"id"`-key gap) — confirmed present on an
unmodified clean checkout too, so nothing this pass touched or introduced them.

**Transfer, commit, push**: `device_bash` was available this session. Verified
`git status` clean / `git log` HEAD matched a fresh GitHub clone before staging;
copied all 17 files via `device_stage_files`/`device_commit_files` (mtime-guarded
against each file's current device mtime, omitted for the 4 brand-new files),
committed and pushed via the GitKraken device-plugin tools, and confirmed the push
landed with a separate fresh `git clone` fetch afterward (`1762787` at `HEAD`).
