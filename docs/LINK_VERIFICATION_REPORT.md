# Careers-Link Verification — Report

**Date:** 11 August 2026

## Summary

The seed company database holds **367 companies** (245 JSE-listed + 122 State-Owned Entities after de-duplication), of which **271 had a careers URL** originally captured. Those URLs were **AI-generated** (they arrived carrying `chatgpt.com` tracking tags), so they could not be trusted without checking.

Full automated verification of all 271 links is **not something that can be done reliably in a one-off pass** — many are JavaScript-heavy portals, some block automated fetching, and this working environment restricts scripted HTTP fetching. The correct, scalable solution is therefore built **into the platform**: the **URL tester** (`backend/app/services/url_tester.py`, exposed at `POST /api/v1/companies/{id}/test-url`) checks every link on import and on schedule, records the HTTP status and whether the page looks like a careers page, and sets each company's `scraping_status` accordingly. This is how all links get verified — continuously, by the system itself.

## Flagship spot-check (manual, 11 Aug 2026)

To size the problem, a sample of well-known employers was checked by hand:

| Company | Result | Action taken |
|---|---|---|
| Gold Fields | ✅ Valid careers portal | Marked `green_confirmed` |
| AECI | ✅ Valid careers portal | Marked `green_confirmed` |
| Thungela Resources | ✅ Valid careers page | Marked `green_confirmed` |
| Old Mutual | ✅ Valid careers page | Marked `green_confirmed` |
| Sanlam | ✅ Valid careers page | Marked `green_confirmed` |
| Absa / Naspers / Nampak | ✅ Valid (landing pages) | Marked `green_confirmed` |
| **Impala Platinum** | ❌ Original `/careers/` returned **404** | **Fixed** → `https://www.implats.co.za/careers-listings.php` |
| **ACSA** | ❌ `/careers` returned **404** | Flagged `needs_real_url` (official path unconfirmed) |
| **Harmony Gold** | ⚠️ **Expired SSL certificate** + robots-disallowed | Flagged `needs_review` |

**Finding:** roughly **1 in 4 flagship links had a problem** (broken, wrong path, or an SSL/robots issue). This confirms the whole set must be validated systematically, not trusted — exactly what the built-in URL tester does.

## Data-quality notes already applied to the seed CSV

- **111 State-Owned Entities** had only a generic `gov.za` contact-directory fallback rather than a real careers page — these are flagged `amber_gov_fallback` / `needs_real_url` and set inactive, so they are captured but not scanned until a real URL is found.
- Tracking tags (`utm_source=chatgpt.com`) were stripped from all URLs.
- A duplicate Telkom SA row (JSE + SOE) was collapsed to the one with a real careers URL.

## Recommended next step

After deploying, run the URL tester across the whole database (a batch job over `POST /companies/{id}/test-url`), then have an administrator review everything that comes back `needs_real_url` or `needs_review` and supply corrected URLs. This turns the 158 currently-scrapeable companies into a verified, trusted list over time.
