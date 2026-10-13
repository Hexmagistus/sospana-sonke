# Roadmap

Reviewed 11 October 2026 against the public sites of GoToCareer, JobSpotter, Unlisted, JobLarper and ScoutJobs (now NeverApply, with scoutjob.me as a separate tech radar), and against the live Sospana Sonke homepage plus this codebase.

Figures below are counted, not estimated. The seed file on this branch has **11,876** employer rows, **231** country names and **5,387** careers URLs (6,489 rows still have no careers URL). The public homepage does not show that total. Until the live directory answers, it shows the built-in snapshot from **7 October 2026**: **3,439** employers with a direct careers link across **187** countries. The homepage replaces those numbers when `GET /companies/stats` answers. Country pages in this change use the snapshot on purpose, and they say the date.

## Where we stand

| | What a visitor can do today | What they cannot |
| --- | --- | --- |
| GoToCareer | Browse official career pages by industry. Featured names and an employer-brand pitch. | No vacancy catalogue, no Africa depth visible on the homepage. |
| JobSpotter | Search about 2,855 verified career pages. Chrome extension finds a page while you browse. | Small index. No government, college or SETA coverage. |
| Unlisted | Search about 1,156,359 openings read from about 27,000 companies through 21 applicant systems. Cards show source, last seen, and pay when the board stated it. Alerts, a tracker, résumé match, and a form-fill extension. | The homepage we read did not show African public-service, municipal, SETA or college depth. |
| JobLarper | Alerts from official boards, a visible last-checked time, and résumé tailoring. Marketing cites a little over 1,500 companies. | Narrow index. Some paid features rewrite a candidate's history. We will not copy that. |
| ScoutJobs / NeverApply | scoutjobs.ai now sends people to NeverApply. scoutjob.me filters official tech roles and offers browser and Telegram alerts. | Tech roles only. |

Sospana Sonke's edge is the directory itself: South Africa first, then the rest of SADC, then the rest of Africa, then other regions; government departments, municipalities, state-owned employers, SETAs, colleges, hospitals and NGOs beside private employers; a direct careers link when we have one; a CV builder; a Career Agent; and an application tracker. The tools are free. Nothing is sent to an employer for the candidate.

The gap that matters most against Unlisted is not the homepage. It is that a candidate still cannot search the vacancies the scanner has already read. The signed-in directory is a list of employers. Open-role counts appear only after a parser has succeeded, and many cards stay "Not counted yet" on purpose.

## How this list is ordered

Impact is what a job seeker or a search engine can do that they cannot do now. Effort is how much of the working app has to change. Admin pages and the phone layout fixes stay as they are. Seed files are out of this list while another session is editing them.

## Now (this change)

These are the highest-impact items that do not invent a statistic or replace a working flow.

1. **Directory search on the list already loaded.** Typeahead on employer name and listing code, plus filters for a careers link, no careers link, open roles we have actually counted, and link scope. Remote and industry are not filters: the employer row has no remote flag and no industry.
2. **Link scope on the card.** "Country filter" when the URL carries `locationCountry` or `Location_Country`. "No country filter" on a known applicant-system host without that parameter. "Employer's page" on the employer's own site. "Third-party board" on a job-board host. The badge does not say the roles are in that country, and it does not say an unfiltered board is global.
3. **Last checked stays the existing badge.** "Last verified …" and "Not yet verified" already come from `last_checked`. The open-role line still says "last checked" only after a count exists. A link with no successful parse stays "Not counted yet".
4. **Public country pages.** `/countries` and `/countries/<slug>` are static, indexable, and ordered South Africa, the rest of SADC, the rest of Africa, then other regions. Each page states the snapshot date and the with-link count. Sign-in returns to that country's directory when the country has a code. The employer list itself stays behind sign-in.
5. **SEO that matches the pages we can expose.** Organization and WebSite schema were already on every page. Country pages add a breadcrumb list. `sitemap.xml` includes `/countries` and each country page. `robots.txt` still hides the signed-in directory, admin, and the CV tools. There is no `SearchAction`: the only keyword search that runs against employers requires sign-in, and a search action has to work without an account.
6. **Homepage country lookup, hero paint, and lighter sections.** A lookup under the hero opens the public country page. It does not pretend to search vacancies. The headline, the lead paragraph and the account buttons are in the first HTML. They used to start transparent and wait for JavaScript, which was the largest-contentful-paint delay on the live homepage (about 6.5 seconds of render delay on 11 October 2026). Wonders and heritage sections use `content-visibility` so the browser can skip painting them until they are near the screen.
7. **Quieter card copy.** "Direct link live" is now "Direct careers link". A stored URL is not proof the board is up.

## Next (high impact, needs a product decision or a larger change)

1. **Search the vacancies we already store.** This is the Unlisted gap. `GET /vacancies` already filters title, place, type, salary, NQF and dates, and it is signed-in and capped. The next step is a fast search over open, non-expired rows, with the employer, country, applicant system, first-seen and last-seen on the card, and a link to the employer's own posting. Do not copy titles from other job boards. Do not guess salary or remote. A missing field stays missing.
2. **Say when a role was last seen.** The vacancy row already has `first_seen_at` and `last_seen_at`. Show them. Close a role only with the existing two-miss rule, not because one fetch was empty.
3. **Refresh the public snapshot.** Country pages and the first paint of the homepage will stay on 7 October 2026 until `directory-snapshot.json` is taken from the live with-link counts again. Do that after the seed import has actually landed in Frankfurt, and do not present the 11,876 seed rows as "employers with a careers link".
4. **Alerts a person can aim.** Notify-me already emails when one employer's page changes. Add the same watch for a country, a category, or a keyword, as a daily mail first. Minute-level alerts need a shorter scan for the employers that person named, which the free 15-minute cron and the 55-second batch cannot promise for the whole directory. Say the real cadence on the control.
5. **Public employer pages, carefully.** One indexable page per employer (name, country, category, link scope, last checked, open-role count) would match GoToCareer and JobSpotter and would let Organization schema point at a real employer. It also publishes the directory without an account. Do it only for rows that already have a careers link, with a canonical URL, and keep notes that are internal research out of the HTML.
6. **Performance of the homepage script.** The landing page is one client component. Splitting the map, heritage and daily spark out of the first load is the next Lighthouse gain. Targets worth holding, once measured on a production build of `/` and `/countries/south-africa`: performance 90 or better on desktop, 70 or better on a slow mobile profile, accessibility 95 or better, SEO 95 or better. Do not claim those until a run records them.
7. **Report a broken link, already there.** The card already posts a report. Keep it on any new employer page.

## Later

| Theme | What to build | Why it waits |
| --- | --- | --- |
| Design system | Tokens, type, dark mode, empty and loading states already exist (`ss-*`, Bricolage Grotesque, Inter). Extend them when a page is touched. Do not restyle admin; the phone table fix depends on `admin-readable`. | A full visual rewrite risks the phone layout and the contrast tests. |
| Industry browse | A real industry on the employer, then a GoToCareer-style index. | `source_type` is category (private, department, college), not industry. Guessing one would be a false claim. |
| Remote filter | A filter that is true only when the posting says remote. | It belongs on the vacancy search, not the employer card. |
| i18n | English, French, Portuguese, Arabic and Swahili for the shell, country names and empty states. Arabic needs layout direction. | Copy is large and some of it is legal (privacy, terms). Translate the public country pages first, then the directory chrome. |
| PWA and low bandwidth | The manifest, service worker and data-saver icon skip already exist. Cache the country index and the last opened country for offline reading. | Do not cache signed-in vacancy or CV payloads on a shared phone. |
| Trust | Verified means last-checked plus a careers link, which the card already says. Add the applicant-system name beside the scope badge once vacancy search exists. | A "verified employer" badge with no date would overclaim. |
| Claim your page | An employer confirms the careers URL. Store the claim as pending. An admin approves. Nothing is paid and nothing jumps the list. | Needs mail, a review queue, and a rule for who may claim a government or university page. |
| Analytics | Count country-page views, directory searches, and outbound careers clicks without storing a search that contains a person's name. | The free host has no analytics product wired. Add a privacy note before any new collection. |
| Growth | Public country pages are the acquisition surface. Share links already exist on cards. A Chrome extension like JobSpotter's is a later client, pointed at our own directory. | The extension is useless until employer pages or a public lookup exist. |
| Monetisation | Donations and the advertiser-spot application already exist. Spots stay labelled sponsored. Do not sell rank in the directory or in vacancy search. | A paid "claim" or featured slot only after the claim queue exists, and the price stays "roughly", matching the current ad form. |

## Explicitly not in the plan

- Browser automation that gets around a bot check. The daily URL check stays plain HTTP. Offline discovery may render a JavaScript shell only when the caller supplies a renderer, and it still obeys robots.txt.
- Inventing vacancy counts, salaries, remote flags, or "live" states.
- Publishing the seed research notes, or treating a blank careers URL as a working link.
- Copying résumé features that backfill a work history the candidate did not do.

## Measured on 11 October 2026

Lighthouse 12.8.2. Before is the live homepage. After is this production build on the local machine, so the best-practices dip is the homepage calling a local API that was not running (`127.0.0.1:8000`), which the live site does not do.

| Page | Form | Performance | Accessibility | Best practices | SEO | Largest paint | Speed index |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Live homepage, before | Mobile | 73 | 95 | 100 | 100 | 7.2 s | 4.6 s |
| Earlier build this branch | Mobile | 75 | 95 | 93 | 100 | 7.4 s | 1.5 s |
| This build, homepage | Mobile | 93 | 95 | 93 | 100 | 3.1 s | 1.7 s |
| This build, homepage | Desktop | 100 | 95 | 93 | 100 | 0.7 s | 0.4 s |
| Earlier `/countries/south-africa` | Mobile | 85 | 100 | 100 | 100 | 4.4 s | 1.1 s |

The homepage headline is server HTML in a system face, with the display fonts not preloaded. Mobile performance moved from 75 to 93. The lead paragraph is still the largest element, and about 2.7 s of the 3.1 s paint is still render delay under the simulated slow phone. Best practices stays 93 on this machine because the page calls `127.0.0.1:8000`, which is not running here. The live site calls Frankfurt instead.

## Suggested order of the next sessions

1. Public employer pages for rows that have a careers link.
2. Daily alerts by country, category and keyword, reusing the notify-me mail path.
3. French and Portuguese on `/countries` and `/jobs`, then Arabic and Swahili.
4. Re-measure `/countries/south-africa` after the snapshot grew to 207 country pages.
