# Phase 2 — Build Status

Phase 2 continues the module-by-module discipline. First module below is complete.

## ✅ Automated application submission (blueprint sections 13, 14, 28)

The defining Phase 2 capability — **safe, policy-bound automated submission** — is built and tested.

**How it stays safe (the order of checks):**

1. **Global kill-switch** — `AUTOMATION_ENABLED` defaults to **False**; automation is opt-in.
2. **Per-source policy** — each company has an admin-set `automation_mode` (`auto` / `assisted` / `manual` / `disabled`) plus `requires_login` / `has_captcha` hints. Only `auto` ever submits; `assisted`/`manual`/`disabled` fall back to a prepared, action-required package.
3. **Live blocker detection** — the page is analysed for **CAPTCHA, login walls, MFA, and required file uploads**. If any are present, the engine **stops and hands back to the candidate** — it never bypasses them (blueprint section 28).
4. **Truthful form-filling** — fields are mapped to the candidate's real profile values only; any **required** field it cannot truthfully fill becomes an `UNKNOWN` that forces candidate input rather than a guess.

Only when all four pass does the Playwright submitter fill and submit. Every outcome
(submitted / action-required / failed) is written to the application's audit trail.

**Components** (`backend/app/automation/`): `detector` (blockers + form-field extraction),
`planner` (truthful field mapping), `base` (types + `Submitter` interface),
`playwright_submitter` (production, headless Chromium), `mock_submitter` (tests),
`engine` (orchestration). **Routes:** candidate `POST /applications/{id}/auto-submit`
(subscription-gated) and admin `PUT /companies/{id}/automation-policy`. **Frontend:** a
"Try automated submission" action on the application page.

**Tests:** 11 automation tests (123 total, all passing) — detector flags, field
extraction (single/double/unquoted attributes), truthful planner + unknown-required
flagging, and engine behaviour for auto-submit, CAPTCHA-stop, login-stop,
unknown-required-stop, assisted-no-submit, manual-policy, and the global switch. A
**live Playwright test** drives real headless Chromium against a local form server and
asserts the correct values were actually submitted (skips if no browser is present).

**To enable in production:** set `AUTOMATION_ENABLED=true` and `PLAYWRIGHT_EXECUTABLE_PATH`
to the deployed Chromium, then set individual companies to `automation_mode=auto` via the
admin policy endpoint **only** where their terms permit automated submission (get legal
sign-off first — blueprint section 29).

## ✅ Account security — MFA (TOTP) + password reset (blueprint section 27)

- **MFA (TOTP)** — `POST /auth/mfa/setup` returns a secret + `otpauth://` provisioning URI (QR-ready); `/mfa/enable` and `/mfa/disable` require a valid authenticator code; login is **MFA-gated** (an account with MFA on must supply a valid `otp_code` or login is rejected). Codes verified with a ±30s window.
- **Password reset** — `POST /auth/password-reset/request` (no account enumeration — always 200; emails a token, returns it in non-production for testing) and `/password-reset/confirm` (token + new password).
- **Frontend** — a Security page to enrol/enable/disable MFA, and the login form prompts for the authenticator code when required.
- **Tests:** 5 (128 total, all passing) — full MFA enrol → gated login → disable cycle, wrong-code rejection, password-reset happy path, no-enumeration, bad-token, and short-password rejection.

## ✅ Website-change detection alerts (blueprint section 23)

When a careers source fails repeatedly (reaches `SOURCE_FAILURE_ALERT_THRESHOLD`, default 3, edge-triggered so it fires once per breakage episode) or its structure appears to change (returned 0 vacancies after previously having some), the scanner raises a **dashboard notification to every administrator**. Tested: 3-strike failure alert and empty-after-nonempty structure-change alert.

## ✅ Interview preparation (blueprint Phase 3 pulled forward)

`POST /matches/{id}/interview-prep` generates truthful prep from the match: **likely questions** (built from the vacancy's real hard/soft requirements + role/company), **talking points** (from the match's own reasons), **watch-outs** (from its gaps), and general tips. Persisted and retrievable; surfaced on the match page in the frontend. Tested (generation content + ownership).

## ✅ JavaScript-rendered ATS coverage (blueprint section 13)

A `PageRenderer` abstraction (Playwright headless Chromium in production, a mock in tests) executes a page's JavaScript so runtime-injected job data becomes readable, then reuses the existing JSON-LD `JobPosting` parser. Careers URLs on JS-heavy ATSs (**Workday, SuccessFactors, Oracle, Taleo, Jobvite**) are auto-detected as `ats_type=js` and routed through it. Gated by `JS_RENDER_ENABLED` (default off — headless Chromium is memory-heavy; enable on paid infra). **Tests:** JS-host detection, mock-rendered parsing, disabled-switch no-op, and a **live test** proving a page that injects a `JobPosting` via JavaScript is empty when fetched raw but yields the vacancy once rendered.

## ✅ SMS + push notification channels (blueprint section 31)

Same swappable-provider pattern as email: **SMS** (console default + Twilio for prod, sends to the candidate's mobile number) and **push** (console default + FCM interface, sends to registered device tokens via `POST /notifications/push-tokens`). Wired into every candidate notification alongside dashboard + email, each channel toggled by config (`NOTIFY_SMS` / `NOTIFY_PUSH`, both off by default) and recorded per-notification (`sms_sent` / `push_sent`). Tested: SMS on a strong match, push to a registered token, and off-by-default behaviour.

## ✅ Richer analytics (blueprint section 44)

`GET /admin/analytics` returns the business-intelligence funnel (matches → qualified → applications → submitted → interviews → offers) with **conversion rates** (qualified/submit/interview/offer), **top companies by matches**, **most common rejection reasons**, and the **subscription breakdown**. Admin-only; tested for gating and a populated funnel.

## ▶️ Remaining Phase 2 module

| Module | Notes |
|---|---|
| Social sign-in | Google/Microsoft OAuth — needs OAuth app credentials from you; best set up right before deployment. |
