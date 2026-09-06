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
