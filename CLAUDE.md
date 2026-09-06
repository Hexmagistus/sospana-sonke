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
- **Country coverage:** all 16 SADC states are live (`LIVE` array,
  `frontend/src/app/page.tsx`). Next wave — Kenya, Nigeria, Ethiopia, Egypt, Morocco,
  Ghana, Senegal, Uganda, Rwanda, Algeria — is in the `SOON` ("Coming soon") array in
  the same file, not yet built out with real company/vacancy data.
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
