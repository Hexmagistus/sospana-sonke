# Transformation audit

11 October 2026. Evidence is from this repository at `230afa2` (then this branch), the live Frankfurt API, the live site, and the seed file as it stood when read. No secret values are recorded. The seed CSV was not edited.

The binding brief asks for South Africa's intelligent opportunity and data platform. This document is deliverables 1–9. Deliverable 10 is the code on this branch: a deterministic Sospana Intelligence search on the homepage and on `/jobs`, with the midnight-navy and electric-teal hero. It does not add empty product pages.

## 1. Evidence-based assessment

### What is running

| Layer | Evidence |
| --- | --- |
| Frontend | Next.js 15 (`frontend/`), Vercel project `sospana-sonke`, public site `https://sospana-sonke.vercel.app`. |
| API | FastAPI, Render service `sospana-sonke-api-fra`, Frankfurt, free plan, one Uvicorn worker (`render.yaml`). |
| Database | Neon Postgres. `GET /health` on 11 October 2026: `env=production`, `db_pooled=true`, `db_region=eu-central-1`. The health `commit` was `17d7afb` (behind this repo's `main`, which has later seed and Search Console commits). |
| Auth | Email and password (Argon2), optional TOTP, Google ID token, JWT with `token_version` for sign-out everywhere. Admin is `users.role` read from the database on each request. |
| Money | The product is free. `has_active_access()` is always true. Checkout returns 410. Donations can use Paystack when configured; mock checkout is refused in production. Advertiser spots are applications only; nothing is charged in the app. |

This session had no `DATABASE_URL` and no LLM key in the environment. Vacancy-level duplicate rates and province fill rates were not queried in SQL. Public HTTP was used instead.

### Directory and vacancy volume (live, 11 October 2026)

`GET /api/v1/companies/stats`:

| | |
| --- | --- |
| Directory rows | 11,986 |
| Countries (excluding International and Africa buckets) | 229 |
| Rows with a careers link | 4,999 |
| Countries with a careers link | 207 |
| South Africa with a careers link | 879 |

Largest with-link countries: South Africa 879, United States 534, Brazil 435, Zimbabwe 134, Kenya 133, Botswana 120, Japan 116, Namibia 100, United Kingdom 98, Nigeria 93.

`GET /api/v1/jobs` (open, closing date not passed, no advert body):

| Filter | Matching open roles |
| --- | --- |
| None | 29,409 |
| Country South Africa | 3,293 |
| Last seen within 1 day | 10,711 |
| Last seen within 7 days | 27,900 |
| Last seen within 30 days | 29,409 |
| South Africa, last seen within 7 days | 3,175 |
| Title contains "nurse", South Africa | 63 |
| Title contains "intern", South Africa | 301 |
| Title contains "learnership", South Africa | 30 |
| Employer name contains "Mediclinic" | 80 |

A sample title was a real stored role (Philips, North America S&OE Leader) with `application_url`, `first_seen_at` and `last_seen_at`. South African nurse results named Association of Palliative Care Centres, Africa Health Research Institute and Mediclinic Southern Africa.

The built-in homepage snapshot (`frontend/src/data/directory-snapshot.json`, `as_of` 2026-10-11) still says 4,299 with a link and 11,986 in the directory. The live with-link count is 4,999. The homepage replaces the snapshot when `/companies/stats` answers, and it labels which source it used.

### Seed file quality (read only)

`backend/seed/company_database_import.csv`: 11,876 data rows, 231 country names, 6,094 careers URLs, 5,782 blank URLs. Import key (name + JSE code + country) has 0 duplicates.

Careers status counts: `grey_none_verified` 6,308, `green_verified` 1,188, `direct vacancy list` 903, blank status 842, `global_group` 703, `amber_company_route` 492. Notes containing `careers_scope=global`: 703, the same rows as `global_group`.

South Africa in the seed: 1,185 rows, 870 with a URL. Live South Africa with a link is 879. The seed is not a perfect mirror of Frankfurt (boot import, later edits, and the health commit lag).

South African `source_type` values in the seed include JSE 288, MUNI 266, SOE 146, COLLEGE 107, PRIVATE/Private about 206 combined, DEPT 45, NGO 44, UNI 26, SETA 22, HOSPITAL 9. Category is not industry.

### What works

- Public directory counts, public `/jobs` keyword search, public country pages, sitemap, robots rules for signed-in tools, Google Search Console verification meta tag.
- Signed-in directory (South Africa, then SADC, then the rest of Africa, then other regions), colleges, hospitals, universities, NGOs, government, Career Agent, CV builder, application tracker, admin.
- Scanner strategies for Greenhouse, Lever, SmartRecruiters, Recruitee, Workable, Workday CXS, Oracle Candidate Experience, Breezy, Pinpoint, CareerInHR, Cornerstone, MCI, PeopleSoft, simplify.hr, iCIMS, and static HTML. `JS_RENDER_ENABLED` is false. SuccessFactors, Taleo, Jobvite and generic Workday hosts stay `js` and are not fetched.
- Cron from GitHub Actions every 15 minutes: `scan_due_companies` and `close_expired_vacancies`, header `X-Cron-Secret`. A role missing from one successful scan is not closed until a second miss. A passed `closing_date` is excluded from public `/jobs` and from the new search.
- POPIA pieces that exist: policy acceptance, separate alert consent, export, account delete that erases documents and anonymises the user, public Information Officer endpoint.
- Contrast tests read the real CSS tokens. Light body text is held at 7:1.

### What is partial

- Homepage search, before this branch, built a phrase and sent the visitor to register. It did not query the 29,409 stored roles. `/jobs` is a keyword form. The Career Agent's parser is deterministic and behind sign-in, and it falls back to the employer directory when the vacancy index is empty for that query.
- Design system: `ss-*` tokens, light and dark, shared card and empty state. The landing page still mixes a hardcoded cream palette with those tokens. This branch adds a scoped midnight/teal band. It does not restyle the signed-in app.
- Link coverage: 4,999 of 11,986 live rows have a careers URL (41.7%). In the seed, 51.3% have a URL. `grey_none_verified` is the largest status. A stored URL is not treated as proof the board is up.
- Province and city filters exist on the vacancy row as best-effort fields. This session could not measure how many of the 29,409 rows have a province, because that column is not on the public jobs payload.
- Migrations are startup `ALTER TABLE` plus `create_all`. There is no Alembic history.
- CSP is Report-Only. JWTs stay in `localStorage`. Rate limits are in-process on one worker.
- Admin TOTP is optional. PR #70 (open, not merged) is the proposal to require it.
- URL tester and page hasher follow redirects without the scraper's SSRF check. The vacancy fetch path does check. PR #70 proposes closing that gap. This branch does not merge it.
- No product analytics, no Sentry DSN confirmed from this session, no saved-search store.

### What is broken or absent

- No Stats SA, municipal, ward, procurement, GDP, unemployment or census tables. Any answer that needs them would be an invention.
- No RAG corpus, no vector index, no citation graph beyond the source URL and the scan timestamps already on the row.
- Job matching was removed in October 2026. `/matches` returns 410. Recommendations that explain eligibility are not a live feature. The tailor still scores one pasted advert.
- `SECURITY_REVIEW.md` is not on `main`. It is the artefact on open PR #69.
- Scorecard telemetry (search success, task completion, returning users, cost per user) is not collected.
- The public homepage snapshot under-counts careers links versus the live API (4,299 vs 4,999) until the API answers.

### Risks

- Treating the seed file, the snapshot and the live API as one number. They are three populations. This audit keeps them separate.
- A language model on top of thin fields (no advert body on the public API) will sound sure and be wrong. The optional model stays off.
- Publishing employer research notes. The new endpoint does not select `notes` or the advert body.
- PR #70 is the right place for admin 2FA, the Google-link fix, Dependabot and the non-scraper SSRF fix. Landing those in this branch would mix a product change with an owner-held security review.

## 2. Architecture and working functionality

```
Browser (Vercel)
  public: /, /jobs, /countries, /login, /register, /donate, /privacy, /terms
  signed in: /companies, /agent, /tailor, /applications, /dashboard, /admin
        |
        | NEXT_PUBLIC_API_URL
        v
FastAPI (Render Frankfurt, 1 worker)
  public reads: /health, /companies/stats, /jobs, /intelligence/search, /compliance, /ads/slots
  signed-in reads: /companies, /vacancies, /career-explorer
  cron: X-Cron-Secret → scan_due_companies, close_expired_vacancies, test_all_urls
        |
        v
Neon Postgres (eu-central-1, pooler)
  companies, vacancy_sources, vacancies, users, scans, donations, ad_applications
```

A careers URL is the employer's own page or their own applicant-system tenant. robots.txt must allow SospanaSonkeBot. Small employers need an in-country list. Large groups may store a global board marked `careers_scope=global` / `global_group`, and import leaves those pending.

Vacancy identity is fingerprint, then source plus `external_id`, then `content_hash`. `content_hash` still includes the first 2,000 characters of the description, so a wording edit can insert a second row when the external id is missing. Closing is the two-miss rule, or `closing_date`, not a single empty fetch.

## 3. Visual direction

The signed-in app stays on the existing warm-paper and deep-space tokens (`--ss-bg` `#f7f5f0` / `#060b16`, gold `#f5b301` as a fill, navy text). Contrast tests already lock those pairs. A full reskin would fight that work and the phone layout.

This branch adds a scoped band, `.ss-intel`, used on the homepage hero:

| Token | Value | Use |
| --- | --- | --- |
| `--ss-intel-navy` | `#0c1b33` | Hero surface |
| `--ss-intel-charcoal` | `#1c2430` | Reserved for later charcoal surfaces |
| `--ss-intel-paper` | `#f4f7f8` | Search card |
| `--ss-intel-white` | `#ffffff` | Result rows |
| `--ss-intel-text` | `#ffffff` | Title on navy |
| `--ss-intel-muted` | `#d5dde8` | Supporting text on navy |
| `--ss-intel-teal` | `#5eead4` | Accent on navy, and the search button fill |
| `--ss-intel-teal-deep` | `#0f766e` | Links on paper |
| `--ss-intel-ink` | `#0b1220` | Text on paper |
| `--ss-intel-card-muted` | `#3f4a5c` | Secondary text on paper |

Bright teal is not used as small text on white. On navy it is an accent (measured in `themeContrast.test.ts` at 7:1 or better). The button is navy text on teal. Paper cards use the same 7:1 ink and muted pairs as the rest of the light theme. Deep teal links on paper are held at 4.5:1. Motion added here is none; the hero ping dot is a static disc. `prefers-reduced-motion` already stops the greeting marquee.

The hero headline is the brief's line, in the server HTML, in a system face, so the first paint does not wait for the display font. The second paragraph says the answer is limited to stored roles and the directory.

Later stages can carry these tokens into the directory and admin. They should not replace the gold button tests in the same change.

## 4. Top 10 improvements

Ranked by what a person can do with data we already hold, that they cannot do today. Acceptance is testable. Effort is how much of the working app moves.

| # | Improvement | Why it is here | Acceptance |
| --- | --- | --- | --- |
| 1 | Grounded question search over stored roles and the directory | 29,409 open roles and 4,999 careers links exist. The homepage search did not read them. | A question returns counts, source links, last-seen or last-checked dates, limitations, and a not-enough-data state. No advert body, no notes, no invented dataset. Tests cover a nurse query, an expired role, a missing dataset, and a notes leak. **This branch.** |
| 2 | Close PR #70's four highs, separately | Google account linking, mandatory admin TOTP, SSRF on the URL tester and hasher, Dependabot and pip-audit. Owner-held. | Admin password login without TOTP is rejected. A redirect to a private address is refused. CI runs pip-audit. PR #69's review file lands with it or just before it. |
| 3 | Public employer pages for rows that have a careers link | The directory is signed in. Country pages are counts only. | One indexable page: name, country, category, link, last checked, open-role count. Notes stay out. Canonical URL. |
| 4 | Say how full the province and city fields are, then use them in `/jobs` | The new search can filter them. The public jobs form cannot. The fill rate is unmeasured. | A read-only SQL report (owner's database) states the percent of open roles with province, city and salary. `/jobs` gains a province field only after that percent is worth showing. |
| 5 | Refresh the homepage snapshot from Frankfurt | First paint says 4,299 with a link; the API says 4,999. | `directory-snapshot.json` matches a dated `/companies/stats` response, and the page says the date. |
| 6 | Alerts by country, category and keyword | Notify-me is per employer. | A daily mail, same sender, stating the cadence. No minute-level promise. |
| 7 | Deduplicate vacancies that share an external id or fingerprint across wording edits | `content_hash` includes description text. | A fixture where the description changes and the external id does not updates one row. A report of live duplicate groups, not a silent delete. |
| 8 | Alembic, or a written migration log that matches startup DDL | Schema changes are imperative `ALTER`s that skip on lock timeout. | A reversible migration for the next column, with a downgrade tested on sqlite and a staging Postgres. |
| 9 | Privacy-safe telemetry for the scorecard | Search success, task completion and retention are unknown. | Counts of searches and outbound clicks, no raw question stored if it may be a person's name, disclosed on the privacy page before collection. |
| 10 | One sourced public dataset, South Africa first | The brief's map and research sections need a real layer. | A table with publisher, URL, date, licence and a column dictionary. The UI shows those, and refuses a cause claim. Empty state if the file is not loaded. |

Not in this list: a second visual system on every page, municipal ward maps without a source, an LLM that writes the answer, paid rank in search.

## 5. Product architecture

One data foundation: `companies`, `vacancy_sources`, `vacancies`, plus the user, document and application tables that already exist.

| Product in the brief | What exists now | Next real slice |
| --- | --- | --- |
| Opportunities | Directory, `/jobs`, tracker, CV builder | The intelligence search (this branch), then public employer pages |
| Intelligence | Career Agent (signed in, deterministic), tailor score for one pasted advert | The same search, still without a model, until a key and a citation test exist |
| Municipal intelligence | Municipality rows and careers links. No ward or budget layer | Item 10, after a permitted file |
| Research institute | None | Do not add a page until a story has a method and a source |
| SME intelligence | Private-company rows | Same search, category filter. No separate page |
| Data API | The public JSON already listed | Document it. Do not add a key gateway until someone pays |
| Insights reports | Candidate PDF report from profile data | Leave it. Do not generate market reports from missing datasets |

Signed-in visitors are still sent from `/` to `/companies`. The same search is on `/jobs`, which does not redirect. Basics stay free. Nothing in this branch sells data.

## 6. Database reliability plan

No table is renamed or dropped in this branch. Rollback of the feature is reverting the commit. There is no migration to undo.

### Canonical model (already mostly true)

- Employer: `companies` row. Identity for import: name + JSE code + country. Country spelling goes through `canonical_country`.
- Board: `vacancy_sources` (URL, ATS type, last success, parser, failure streak).
- Role: `vacancies`. Open means `is_open` and a closing date that is null or not passed. Expired is not deleted.
- Person: `users` and `candidate_profiles`. Consent flags have timestamps. Delete anonymises rather than leaving the profile readable.

### Fields an opportunity needs

Already present and used by the new search when the question asks for them: title, employer, country, location, province, city, employment type, work mode, salary text and parsed min/max, posting date, closing date, application URL, first seen, last seen. Missing on a row stays null. The answer does not fill them.

Still absent, and not invented here: occupation code, NQF as a verified fact (the column is an estimate), learnership flag separate from the title, bursary amount, procurement reference, municipality code, ward.

### Validation, dedupe, provenance, freshness, history

- Validation on the way in already refuses a careers URL that fails the standing rule. The daily URL check is plain HTTP. A bot challenge is not executed.
- Dedupe keys: import key for employers; fingerprint, external id, content hash for roles. Seed import keys: 0 duplicates. Live role duplicates: unknown until a SQL pass (owner access).
- Provenance: `parser_used`, `source_url`, `application_url`, `scan_logs`. The public answer exposes the application or careers URL and the dates, not the parser internals.
- Freshness: of open roles returned by `/jobs`, 27,900 of 29,409 (94.9%) were last seen within 7 days, and 10,711 (36.4%) within 1 day. Every open role in that response was last seen within 30 days. That is the scanner's clock, not the employer's closing clock.
- History: `first_seen_at`, `last_seen_at`, `consecutive_misses`, `lifecycle_status`. Soft delete via `deleted_at`. There is no row-level history table. A later history table should be append-only and reversible.
- Quality checks to add with owner SQL, not in this branch: percent of open roles with province, with application URL, with a duplicate fingerprint, and employers whose `last_checked` is older than 30 days.

### Safe ingestion

Permitted sources remain the employer's own board and, for a large group, the marked global board. No new external dataset is loaded. Notes stay internal.

## 7. Intelligent search and discovery plan

The search that shipped is the first slice of Sospana Intelligence.

1. The question is normalised (length 200, possessives, punctuation).
2. A deterministic parser pulls country (directory names plus a few aliases such as SA, UK, USA), South African province, city (from the scraper's city list; "george" and "newcastle" only count after "in"), category (hospital, university, government, and the other directory groups), employer ("at …"), employment type, work mode, and a freshness window.
3. Words that ask for GDP, unemployment, inflation, crime, census, population, procurement, a municipal budget, Stats SA, election results or a ward are removed and named. If nothing else remains, the answer is not-enough-data and the counts are zero.
4. Remaining words are stemmed only for a short list (nurse, intern, learnership, bursary, scholarship) and matched with `ILIKE` on the title. This is not semantic search.
5. Roles: open, not deleted, closing date not passed. Country matches the employer or the role. Sample of 8, ordered by `last_seen_at`. Count is the full match.
6. Employers: directory rows, notes and favicon bytes deferred. Sample of 8. Careers URL, last checked, and whether the URL check recorded a careers page. Open-role count uses the same helper as the directory. "Not counted yet" when we have not had a structured read.
7. The summary is a template filled with those integers and the newest `last_seen_at` date. Follow-up chips are narrower questions whose own count is greater than zero and smaller than the current count (last 7 days, Gauteng, or South Africa). A follow-up that the parser does not round-trip is dropped.
8. `llm` is `"disabled"`. Cache-Control is `no-store` because a question may contain a person's name. The question is not written to a table.
9. Rate limit 30 a minute per IP. The limiter is off when `ENV=test`.

What this is not: retrieval-augmented generation, a ranking model, eligibility, or a promise. A later model may paraphrase a packet that already contains the count, the links and the limitations. It may not add a fact. That layer stays unwired until a key exists and a test asserts every sentence is grounded in the packet. Prompt injection is currently just another keyword string; there is no instruction channel to hijack.

Example questions shown in the box were checked against live `/jobs` on 11 October 2026 (nursing 63, intern 301, learnership 30, Mediclinic 80). If the index moves, the box still runs the question and will say when nothing matches.

## 8. Security, privacy and performance checklist

| Check | Status |
| --- | --- |
| Secrets only in the host environment | Holds. This session printed no secret values. None of the relevant keys were set here. |
| Admin re-read from the database | Holds. Mandatory admin TOTP does not. Leave it to PR #70. |
| Google sign-in links on email alone | Holds as a risk. PR #70. Do not merge it from this work. |
| SSRF on vacancy fetch | Holds (`assert_safe_fetch_url`). URL tester and hasher still follow redirects. PR #70. |
| Public search does not return notes, advert body, emails, or password material | Holds. Test asserts the note text is absent. |
| Rate limit on the new route | 30/minute. In-memory, one worker. |
| POPIA | No new personal-data store. Questions are not saved. `no-store` on the response. Access logs on Render may still contain the query string; do not ship that string to a third-party analytics tool. |
| Consent | Unchanged. Search works without an account. |
| Prompt injection | No model is called. The question cannot change the SQL shape; values are bound parameters. |
| Uploads | Unchanged. CV checks stay on the existing path. |
| Client secrets | No new key in the frontend bundle. |
| CSP | Still Report-Only. The new request goes to the same API host already in `connect-src`. |
| Performance | Search is two counts and a limit-8 read, same shape as `/jobs`. Title `ILIKE '%word%'` will not use a btree. Acceptable at 29k rows; revisit if the table grows an order of magnitude. Homepage headline stays server HTML in a system face. Display fonts stay not preloaded. |
| Accessibility | New pairs are in `themeContrast.test.ts`. The form has a label, the result region is `aria-live`, follow-ups are buttons, links have text. A `noscript` link points at `/jobs`. |
| Dependabot / pip-audit | Not on `main`. PR #70. |

## 9. Roadmap and scorecard

### Stages

| Stage | Change | Reversible by |
| --- | --- | --- |
| 0 | This audit | Deleting the file |
| 1 | Intelligence search, hero tokens, tests. **This branch.** | Revert the commit. No schema change. |
| 2 | PR #70, after the owner reviews it. Not this branch. | That PR's own commits |
| 3 | Public employer pages for linked rows | Revert. No notes in the HTML. |
| 4 | Snapshot refresh from a dated Frankfurt stats response | Replace the JSON |
| 5 | SQL quality report (province fill, duplicate fingerprints, stale `last_checked`) using the owner's database | Read-only |
| 6 | Keyword alerts, daily | Revert the mail job |
| 7 | First sourced public dataset, with licence and date on the screen | Drop the table |
| 8 | Optional model paraphrase, only with a key and a grounding test | Leave the key unset; `llm` stays `disabled` |

### Scorecard baselines (11 October 2026)

| Measure | Baseline | How it was counted |
| --- | --- | --- |
| Open roles stored | 29,409 | `GET /jobs` `matched` |
| Open roles last seen within 7 days | 27,900 (94.9%) | `max_age_days=7` |
| Open roles last seen within 1 day | 10,711 (36.4%) | `max_age_days=1` |
| South Africa open roles | 3,293 | `country=South Africa` |
| Directory rows | 11,986 live; 11,876 seed | stats API; CSV |
| Rows with a careers URL | 4,999 live (41.7%); 6,094 seed (51.3%) | stats `with_link`; CSV non-blank `careers_url` |
| Duplicate employer import keys | 0 | CSV name + JSE code + country |
| Duplicate stored roles | Not measured | Needs database access |
| Province / city fill | Not measured | Column is not on the public jobs payload |
| Search success | Not instrumented | No analytics. Manual: the four example questions hit `/jobs` with the counts above. |
| Task completion, time to result, returning users, conversion, retention, cost per user | Not instrumented | No analytics product is wired |
| Recommendation usefulness | Not applicable | Per-user matching is off. This search does not rank. |
| Accessibility defects in the new band | 0 token pairs under the thresholds in section 3 | `themeContrast.test.ts` |
| Homepage performance | See the Lighthouse table below | Same day's runs |
| Trust | A URL check date is shown only when `last_checked` is stored. Otherwise the line is "No URL check recorded yet." | Code |

### Lighthouse

Lighthouse 12.8.2. Before is the live homepage. After is a production build of this branch on this machine. The after run calls the Frankfurt API for directory stats (that host is up) and does not execute the new search, which only runs after a click. Mobile uses the default simulated slow phone.

| Page | Form | Performance | Accessibility | Best practices | SEO | Largest paint | Speed index |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Live homepage, before | Mobile | 86 | 95 | 100 | 100 | 4.1 s | 2.8 s |
| Live homepage, before | Desktop | 100 | 95 | 100 | 100 | 0.7 s | 0.5 s |
| This branch, homepage | Mobile | 95 | 95 | 96 | 100 | 2.8 s | 1.7 s |
| This branch, homepage | Desktop | 100 | 95 | 96 | 100 | 0.6 s | 0.4 s |

Best practices is 96 on this machine because the production build asks the Frankfurt stats API from `http://127.0.0.1:3000`, and that host does not send an allow-origin header for a localhost page. The console error is that CORS refusal. The same audit on the live site, before this change, scored 100. Accessibility stays 95. The two failing checks are the existing country select (no label) and a heading that skips a level. They are outside the new search.

An earlier local build on 11 October, before this hero, recorded homepage mobile performance 93, accessibility 95, best practices 93, SEO 100, largest paint 3.1 s. The live site earlier the same day was mobile performance 73. Those figures are not reused as this change's after score.

## 10. What this branch changes

- `GET /api/v1/intelligence/search?q=` — deterministic parser and template answer.
- Homepage hero copy and the intelligence band. The search box submits to that endpoint and renders roles, employers, limitations and follow-ups.
- The same box on `/jobs`, above the existing keyword form, so a signed-in visitor (who is redirected away from `/`) can use it.
- Contrast tests for the new tokens.
- This file.

Not changed: seed CSV, snapshot JSON, scanner, auth, PR #69, PR #70.
