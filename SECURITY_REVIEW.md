# Sospana Sonke security review

**Date:** 9 October 2026
**Scope:** read-only review of the FastAPI backend, the Next.js frontend, deployment config, dependency pins, GitHub repository settings, and a few non-destructive requests to the live site.
**Live surfaces checked:** `https://sospana-sonke.vercel.app` and `https://sospana-sonke-api-fra.onrender.com`.
**Method:** read the current code (this is a fresh pass, not a copy of the 24 September 2026 audit), search git history for secret-shaped strings, run `pip-audit` against `backend/requirements.txt` and `npm audit --package-lock-only` against `frontend/package-lock.json`, and send single ordinary HTTP requests. No fuzzing, no login attempts against real accounts, no writes to production, and no change to application code.

This review reduces risk. It does not make the platform immune to attack.

## Immediate rotation

No live secret was found in the tracked tree or in git history. Placeholder strings in `backend/.env.example` (`CHANGE-ME`, `sk_live_xxx`, `postgresql://user:pass@host/...`) and the fake host `ep-example` with the password `s3cret` in tests are not credentials. Nothing in the repository needs rotating because of this review.

Render environment values, GitHub Actions secret values, the Neon password, and the Vercel dashboard were not readable from here. This review cannot prove those dashboards are clean. If a secret has ever been pasted into a pull request, a log, or a chat, rotate that one separately.

The Google OAuth client id is public by design (it is sent to every browser). It is not a secret and is not listed below.

## Critical

None found.

Unauthenticated calls to the live API returned 401 for `/api/v1/companies` and `/api/v1/admin/dashboard`. `/docs`, `/redoc`, and `/openapi.json` returned 404. A wrong Google credential returned 401 (`Invalid Google sign-in`), which means Google sign-in is switched on, and it did not accept the bad token. A cron call with no secret returned 401 (`Invalid cron secret`), which means `CRON_SECRET` is set on the Frankfurt service. The vacancy scraper refuses non-public addresses before each hop.

## High

### H1. Google sign-in takes over an existing account and skips the authenticator

**Evidence**

- `backend/app/api/routes_auth.py` lines 224–242: if Google’s tokeninfo endpoint says the email is verified, the handler loads any user with that email and issues access and refresh tokens. It never checks the password, and it never calls `verify_totp`.
- The same file, lines 177–180, checks the authenticator only on the email-and-password login.
- Live: `POST /api/v1/auth/google` with a dummy credential returned HTTP 401, so the endpoint is configured. A 503 would have meant it was off.

**Risk**

Anyone who can obtain a Google sign-in for an address that already has a Sospana Sonke account becomes that user. That includes an administrator who set up an authenticator. The six-digit code is never asked. A phished Google session on the admin’s Gmail is a full admin session here.

A second path uses the same code. Registration does not require the person to prove they own the inbox (`get_current_user` in `backend/app/core/deps.py` lines 14–35 never reads `email_verified`, and login at `routes_auth.py` lines 151–188 does not either). Someone can register `victim@example.com`, use the account immediately, and still know the password. When the real owner later presses “Continue with Google”, they land in that existing row. The first person keeps password access.

**Fix**

- After a successful Google check, if `mfa_enabled` is true, require a valid TOTP before issuing tokens. Do this for every role, and treat admin as mandatory (see H2).
- Do not attach Google to an existing password account until that account’s email is verified, or until the person enters the current password or a one-time email code.
- Refuse API access while `email_verified` is false, except for verify, resend, and logout. Registration can keep returning 409; the important part is that an unverified row cannot hold CVs or become the account Google joins.

### H2. Authenticator is optional for administrators

**Evidence**

- `backend/app/models/user.py` line 38: `mfa_enabled` defaults to false.
- `backend/app/api/routes_auth.py` lines 296–331: setup, enable, and disable are all voluntary.
- `backend/app/services/bootstrap.py` lines 95–99: the boot-time admin is created with a password and `email_verified=True`, and with MFA left off.
- `require_admin` in `backend/app/core/deps.py` lines 38–41 checks `user.role == "admin"` and does not check `mfa_enabled`.

**Risk**

One phished or reused password is enough for the admin dashboard: every user email and mobile number (`GET /api/v1/admin/users`), CSV import, careers-URL edits, and the scan trigger. The authenticator feature exists and is unused unless that person turned it on.

**Fix**

For `role == "admin"`, refuse login (password and Google) until TOTP is enabled, and refuse `POST /auth/mfa/disable` for admins. Keep the secret out of the API response after enrolment. Store it encrypted with a key that is not the JWT signing key, so a database copy alone does not mint valid codes.

### H3. Scheduled fetches follow redirects with no private-address check

**Evidence**

The vacancy scanner does this correctly. `request_with_backoff` in `backend/app/scraper/politeness.py` lines 140–184 calls `assert_safe_fetch_url` on the original URL and on every redirect, and it uses `follow_redirects=False`.

These paths do not:

- `backend/app/services/url_tester.py` lines 38–45 and 95–103 build an httpx client with `follow_redirects=True` and never call `assert_safe_fetch_url`. `test_url_sync` then reads `resp.text`.
- `backend/app/scheduler/jobs.py` lines 343–356 runs that tester on a schedule against every active company that has a careers URL.
- `backend/app/services/link_check_service.py` lines 45–64 does the same with `follow_redirects=True` and reads the body to hash it.
- The icon job (`backend/app/scheduler/jobs.py` lines 200–204) also uses `follow_redirects=True`. `backend/app/services/logo_service.py` lines 164–171 checks the URL it was given and the final `resp.url`, but httpx has already followed every hop in between, including a private address in the middle of the chain.

`assert_safe_fetch_url` itself (`backend/app/scraper/ssrf.py` lines 58–85) blocks non-http schemes, localhost names, and private, loopback, link-local, and cloud-metadata addresses, including IPv4-mapped IPv6. That helper is simply not on the scheduled URL-test and content-hash clients.

**Risk**

The Frankfurt server fetches thousands of third-party careers URLs on a timer. If any of those sites redirects (an open redirect, a compromised page, or a careers URL an admin imported) to a link-local or private address, the server requests it and reads the body. That includes cloud metadata addresses such as `169.254.169.254`. The vacancy parser would have stopped. The health checker and the page hasher will not.

A careers URL only enters the database through the seed CSV, an admin import, or an admin edit. The seed file is what production re-imports on boot (`AUTO_SEED=true` in `render.yaml` line 29). A merged change to that CSV, or a redirect on a site already in the list, is enough. The response is not handed back to anonymous visitors; it is processed on the server (status, “looks like careers”, content hash).

**Fix**

Use the same manual redirect loop as `request_with_backoff` for `test_url`, `test_url_sync`, `check_company_content`, and icon fetches. Call `assert_safe_fetch_url` before every hop. Pin the DNS result you just checked to the connection if the HTTP client allows it, so a name cannot resolve to a public address during the check and a private address a moment later. Keep SVG out of icons (that part is already in place).

### H4. The GitHub repository is public, and Dependabot alerts are off

**Evidence**

- `gh repo view` reports `visibility: PUBLIC` for `Hexmagistus/sospana-sonke`.
- `GET /repos/Hexmagistus/sospana-sonke/dependabot/alerts` returns “Dependabot alerts are disabled for this repository.”
- There is no `.github/dependabot.yml`.
- Repository rulesets returned an empty list.
- Classic branch protection could not be read: the API token received HTTP 403 (“Resource not accessible by integration”). Secret scanning and code scanning returned the same 403, so this review cannot say whether those GitHub features are on.
- `render.yaml` lines 29–31: production boots with `AUTO_SEED=true` and `PAYMENT_PROVIDER=mock`. A deploy imports `backend/seed/company_database_import.csv`.
- CI (`.github/workflows/ci.yml`) runs pytest, `tsc`, and `npm audit --audit-level=high`. It does not run `pip-audit`. Workflows that hold `CRON_SECRET` are `schedule` and `workflow_dispatch` only. None use `pull_request_target`.

**Risk**

The full design of auth, the cron header, and the CV storage is readable by anyone. That is survivable when the secrets stay in Render and GitHub. It becomes a problem because production loads the seed file from this repo on every boot, Dependabot will not open an alert for the vulnerable pins in the Medium section below, and this review could not confirm that `main` requires a review before it updates the live site.

**Fix**

- Turn on Dependabot alerts and secret scanning, and add a `dependabot.yml` for pip and npm.
- On `main`, require a pull request and the CI check before merge, and disallow force-pushes. Confirm that in the GitHub UI, because this token could not.
- Add `pip-audit -r backend/requirements.txt` to CI and fail the job on a known vulnerability in a package the app actually calls.
- Keep the repo public only if that is a deliberate choice. The CV and account code does not need to be public for the product to work.

## Medium

### M1. Sessions live in localStorage, and the refresh token is reusable

**Evidence**

- `frontend/src/lib/api.ts` lines 8–25: access and refresh tokens are stored under `sospana_access_token` and `sospana_refresh_token` in `localStorage`.
- `backend/app/core/security.py` lines 42–53: access tokens last `ACCESS_TOKEN_EXPIRE_MINUTES` (30) and refresh tokens last 14 days. Both are HS256 JWTs signed with `SECRET_KEY`. `decode_token` pins the algorithm to HS256.
- `backend/app/api/routes_auth.py` lines 245–256: `POST /auth/refresh` issues a new pair and leaves the presented refresh token valid until it expires or `token_version` changes.
- `frontend/next.config.mjs` lines 7–34, confirmed on the live homepage: `Content-Security-Policy-Report-Only` with `script-src 'self' 'unsafe-inline'`. There is no enforcing `Content-Security-Policy`.
- The only `dangerouslySetInnerHTML` in the frontend is `JSON.stringify` of the site’s own JSON-LD in `frontend/src/app/layout.tsx` line 141. No other HTML injection sink turned up.

**Risk**

There is no cookie, so cookie flags (HttpOnly, Secure, SameSite) do not apply, and a classic cross-site form post cannot attach the bearer token. The trade-off is that any script that runs on the Vercel origin can read both tokens. Today the app does not render job text or CV text as HTML, so that script is not already in the pages. The report-only policy would not stop it: `unsafe-inline` is allowed, and report-only never blocks. A stolen refresh token keeps working for up to 14 days even after the browser has refreshed, because the old token is not revoked. `POST /auth/logout-all` does revoke every token, and it is the only logout that does.

**Fix**

Move the refresh token to an `HttpOnly; Secure; SameSite` cookie scoped to the API host, and rotate it on every refresh (detect reuse by storing a hash of the current token). Keep the access token short. Enforce the CSP after a report-only week, with a nonce for the Next.js bootstrap script instead of `unsafe-inline`. Until then, treat any new HTML rendering of pasted job text or comments as a session-theft bug.

### M2. CV uploads are type-sniffed only, and the bytes sit in the application database

**Evidence**

- `backend/app/services/malware_scan.py` lines 60–72: size, extension (`pdf`, `docx`, `txt`), and magic bytes. ClamAV runs only when `CLAMAV_ENABLED` is true.
- `backend/app/core/config.py` lines 81–85: `CLAMAV_ENABLED` defaults to false. `render.yaml` does not set it.
- A DOCX is accepted when the file starts with ZIP magic (`malware_scan.py` lines 21–22). `backend/app/services/cv_extract.py` lines 16–44 parses the PDF and the DOCX with no page cap and no decompression cap.
- `POST /cv` (`backend/app/api/routes_cv.py` lines 77–111) has no rate limit and no per-user storage quota. The read stops at `MAX_UPLOAD_MB + 1` (8 MB). The global body cap in `backend/app/main.py` lines 97–108 is 30 MB and only applies when `Content-Length` is set.
- Production storage is the `stored_files` table (`backend/app/services/storage.py` lines 146–163 and `backend/app/models/stored_file.py`). Downloads go through authenticated routes that check `user_id` (`routes_cv.py` lines 134–141, `routes_documents.py` lines 58–68 and 78–88). There is no public object URL. Keys are server-built (`cv/{user.id}/{cv.id}.{ext}`). The local-disk backend strips `..` (`storage.py` lines 39–44); production does not use that backend.
- The download header is `Content-Disposition: attachment; filename="{original filename}"` (`routes_cv.py` line 141). The filename is the client’s name, cut to 255 characters, with no further stripping.

**Risk**

A signed-in user can upload a ZIP renamed to `.docx`, or a PDF built to waste CPU, and the free 512 MB process will parse it. Nothing scans for malware. Filling Neon (the free database is small) is a matter of repeating 8 MB uploads; there is no quota. The files are not world-readable, which is the right shape, and they are also not encrypted separately from the database. A database backup or a stolen `DATABASE_URL` is a copy of every CV and every generated letter. The filename in the download header is a foot-gun if a future proxy forwards raw header bytes; strip quotes and control characters now.

**Fix**

- Cap PDF pages (for example 30) and ZIP expansion before parsing. Reject a DOCX whose uncompressed size or file count is absurd.
- Add a per-user upload quota and a rate limit on `POST /cv`.
- Encrypt `stored_files.data` with a key that lives only in the environment, or move the bytes to a private bucket with short-lived signed download URLs. Keep the bucket private.
- Turn on ClamAV only on a host that can run it. On this free instance, say in the privacy notice that uploads are type-checked and not virus-scanned, and keep the parser caps.
- Set the download filename from a fixed pattern (`cv.pdf`), not from the client’s string.

### M3. A person’s copy of their data leaves out the CV, and a Google-only account must know a password to delete it

**Evidence**

- `GET /api/v1/account/export` (`backend/app/api/routes_account.py` lines 43–96) returns the account, profile fields such as city and occupation, tips, and messages. The function’s own note says uploaded CV files are not attached. Education, work history, skills, and extracted CV text are not in `_export_profile` (lines 99–113).
- `POST /api/v1/account/delete` (lines 214–220) returns 403 unless `verify_password` succeeds. Google sign-up stores a random password the person never saw (`routes_auth.py` lines 227–230). They can use “forgot password” first, if email delivery is working.
- Deletion itself does erase stored files, extracted text, generated documents, and profile rows (lines 170–211 and 233–254), then anonymises the email. That part is in place.
- `mfa_secret` is a plaintext column (`backend/app/models/user.py` line 39).
- The public POPIA contact is `INFORMATION_OFFICER_EMAIL`, defaulting to a personal Gmail address in `backend/app/core/config.py` lines 107–108, and `GET /api/v1/compliance` publishes it.

**Risk**

POPIA section 23 is a copy of the personal information you hold. The export omits the CV text and the work history, which are the sensitive parts. A person who only ever used Google cannot complete erasure until they invent a password via the reset email. If mail is down, they cannot delete the account. A database copy includes every TOTP secret, so MFA does not survive a database leak.

**Fix**

- Include extracted CV text, education, work history, skills, and certifications in the export. Offer the original file as a separate authenticated download in that same flow.
- Accept a fresh email code, or a TOTP code, as an alternative to the password on delete. Google-only users should not be blocked.
- Encrypt `mfa_secret` at rest.
- Receive data-subject mail at a mailbox the organisation controls, and set that address in the environment.

### M4. Rate limits live in the process, and they reset when the free instance wakes

**Evidence**

- `backend/app/core/rate_limit.py` line 19: one in-memory `slowapi` limiter, keyed by the trusted client IP (`backend/app/core/client_ip.py`). It is disabled when `ENV=test`.
- Login is 10 per minute per IP (`routes_auth.py` line 152) plus a database lockout of 10 failures and 15 minutes (`config.py` lines 37–40, `routes_auth.py` lines 163–173). The lockout survives a restart. The per-IP counter does not.
- `render.yaml` line 21 runs one Uvicorn worker. Render’s free service sleeps and restarts.

**Risk**

The account lockout is the control that actually stops password guessing, and it is stored in Postgres. The per-IP ceilings (login, register, reset, cron, directory) disappear on every restart and are not shared if a second instance is ever added. A restart also clears the in-process directory caches, which is fine. It is not fine for the cron secret: `POST /cron/run/{name}` is limited to 30 per minute in that same memory (`routes_cron.py` line 40).

**Fix**

Keep the database lockout. Before adding a second instance, move the limiter to a store that survives restarts. Until then, make `CRON_SECRET` long (at least 32 random bytes) and rotate it if it has ever been copied into a log. The comparison is already `hmac.compare_digest`, and the secret is header-only.

### M5. Known vulnerable pins, and CI does not audit Python

**Evidence**

`pip-audit -r backend/requirements.txt --disable-pip --no-deps` on 9 October 2026 reported:

| Package | Pinned | Fix | What it means here |
|---|---|---|---|
| `orjson` | 3.10.15 | 3.11.6 | `PYSEC-2026-107` / CVE-2025-67221, unbounded recursion in `orjson.dumps`. The app calls `orjson.dumps` on server-built payloads in `backend/app/core/http_cache.py` line 37, not on an arbitrary client JSON tree. |
| `PyJWT` | 2.13.0 | 2.15.0 | Fourteen IDs, most of them about mixing HMAC with a public key, JWKS fetch redirects, or PEM parsing. This API decodes with `algorithms=["HS256"]` and a server secret only (`security.py` lines 16 and 104–108). It does not use `PyJWKClient`. Upgrade anyway; the pin is the vulnerable version. |
| `pypdf` | 6.18.1 | 6.19.0 | `PYSEC-2026-4157`, `4159`, `4160`: crafted PDFs that burn CPU or memory via page labels, embedded files, or form flattening. `cv_extract.py` uses `PdfReader` and `extract_text`, which is a narrower path. Untrusted PDFs are still parsed on a 512 MB process (see M2). |

`npm audit --package-lock-only` reported 4 moderate and 0 high:

- `next` 15.5.26 is inside `>=15.0.0 <15.5.27` for GHSA-4jqv-mc3x-m676 and GHSA-mcj8-r9mp-w47p (cache poisoning of SSG/ISR). The advisories describe self-hosted applications. This frontend is on Vercel. The patched 15.x release is 15.5.27.
- `postcss-selector-parser` (via Tailwind’s nested plugin) GHSA-rj75-hqrm-r3gf, a CPU-exhaustion bug in a dev tool. CI’s `npm audit --audit-level=high` does not fail on moderate.

**Risk**

The Python issues are real pins with published fixes. The current call sites avoid the worst PyJWT and orjson tricks. They will not stay safe if someone later decodes tokens with a wider algorithm list or dumps client JSON through orjson. CI would not notice a new Python advisory.

**Fix**

Bump `orjson` to 3.11.6 or newer, `PyJWT` to 2.15.0 or newer, and `pypdf` to 6.19.0 or newer. Move Next.js to 15.5.27 or newer. Add `pip-audit` to `.github/workflows/ci.yml`. Re-run the CV upload test after the pypdf bump.

### M6. Database TLS is not forced in code, and there is no backup drill in the repo

**Evidence**

- `backend/app/db/session.py` lines 57–74 build psycopg2 arguments and never set `sslmode=require`. The example URL in `backend/.env.example` line 6 includes `sslmode=require` as a comment for the operator to paste.
- Live `GET /health` returned `{"status":"ok","env":"production","db_pooled":true,"db_region":"eu-central-1", ...}` with `Cache-Control: no-store` and the security headers below. The region is the AWS region embedded in the Neon hostname. The response does not include the user, password, or endpoint id (`describe_database` in `session.py` lines 33–46).
- No script, workflow, or doc in this repo takes a backup or tests a restore.

**Risk**

If the Neon URL on Render was saved without `sslmode=require`, the driver is allowed to fall back to cleartext. This review could not see that URL. CV bytes and password hashes travel on that connection. Neon’s own retention is also invisible here. A free database with no tested restore is one bad migration away from losing every account.

**Fix**

In `postgres_connect_args`, set `sslmode=require` for every non-SQLite URL. In the Neon console, confirm point-in-time restore is on, take a snapshot, and restore it once to a scratch project. Write down the date and who did it. Keep that note out of the public repo if it contains project ids you would rather not publish; the fact that a restore was tested can live here.

## Low

### L1. `/health` names the environment, the git commit, and the database region

**Evidence.** Live body on 9 October 2026: `env` `production`, `db_pooled` true, `db_region` `eu-central-1`, plus `RENDER_GIT_COMMIT`. Code: `backend/app/main.py` lines 154–169.

**Risk.** Confirms the stack to anyone who asks. The commit is already public because the repo is public.

**Fix.** Keep `status` and `commit` if you need them for deploys. Drop `env` and `db_region` from the public body, or require the cron header for those two fields.

### L2. Registration tells you when an email is already taken

**Evidence.** `backend/app/api/routes_auth.py` lines 91–92 return 409. Password reset does the opposite and always returns the same sentence (lines 336–361). A locked account returns 429 with a lock message (lines 164–165) instead of the generic 401, so a locked inbox is distinguishable from a wrong password.

**Risk.** Address harvesting and a small signal that an account is temporarily locked.

**Fix.** Return the same 200 for register-if-you-want and send “you already have an account” by email. Keep the lockout, and use the same 401 text as a bad password.

### L3. Passwords can be any 8 characters

**Evidence.** `backend/app/schemas/auth.py` line 18: `min_length=8`, `max_length=128`, no other rule. Hashing is Argon2 via `PasswordHasher()` (`backend/app/core/security.py` lines 15–20), which is the right algorithm.

**Risk.** `Password123` meets the rule. Argon2 makes offline guessing slow after a database leak; it does not stop online guessing of a very common password inside the 10-failure lockout.

**Fix.** Check new passwords against a small leaked-password list (HIBP’s k-anonymity range API, or a local list of the worst few thousand). Keep Argon2.

### L4. A few tokens still travel in the query string

**Evidence.** `GET /api/v1/auth/verify?token=` (`routes_auth.py` lines 112–113 and 137–148). The digest unsubscribe page puts the token in the form action (`routes_notifications.py` lines 55–67) and HTML-escapes it. `backend/app/core/logging.py` lines 29–44 redacts `token`, `code`, `key`, `secret`, and bare JWTs from log lines, including uvicorn’s access log.

**Risk.** The token can still land in a browser history, a Referer on a future link, or a log shipper that runs before this filter. The unsubscribe POST is a capability URL: whoever has the link can unsubscribe, which is what the link is for. GET does not change the preference.

**Fix.** Keep GET verify as a landing that POSTs the token in the body. The scrubber can stay.

### L5. The homepage sends `Access-Control-Allow-Origin: *`

**Evidence.** Live response headers for `https://sospana-sonke.vercel.app/` include `access-control-allow-origin: *`. The API does not. A request with `Origin: https://evil.example` and one with `Origin: https://sospana-sonke.vercel.app.evil.com` received no `Access-Control-Allow-Origin`. `Origin: https://sospana-sonke.vercel.app` and a `hexmagistus1` preview host did. Code: `backend/app/core/origins.py` lines 15–18 and `backend/app/main.py` lines 75–88 (`allow_credentials=True` only together with that allow-list).

**Risk.** Any site can read the public HTML of the marketing page. The API allow-list is doing its job. Tokens are not in cookies on that HTML response.

**Fix.** Leave the API regex as it is. If Vercel added the star automatically, restrict it only if you later put authenticated responses on the same host.

### L6. Legacy company icons can redirect the browser

**Evidence.** `GET /api/v1/companies/{id}/icon` is unauthenticated on purpose (`routes_companies.py` lines 425–444). When the row has a URL and no stored bytes, the handler returns 302 to that URL (lines 406–410).

**Risk.** A stored `favicon_url` of `https://example.evil` sends the visitor there. New icons are stored as sniffed raster bytes, so this is the leftover URL path.

**Fix.** Redirect only to `http`/`https` URLs that pass `assert_safe_fetch_url`. Otherwise return 204.

### L7. Pasted job text has no maximum length of its own

**Evidence.** `AnalyzeJobRequest.job_description` is `Field(min_length=1)` with no maximum (`backend/app/schemas/job_analysis.py` line 14). `TailorRequest` in `routes_documents.py` lines 24–27 is the same. The 30 MB `Content-Length` cap is the only ceiling.

**Risk.** One signed-in user can store a very large advert and make the tailor path do a lot of work.

**Fix.** Cap the pasted advert at something like 50,000 characters.

### L8. Error tracking is off unless someone set a DSN

**Evidence.** `SENTRY_DSN` defaults to empty (`config.py` lines 162–165). `_init_sentry` returns immediately when it is empty (`logging.py` lines 124–128). Application logs go to stdout with email addresses, query secrets, and JWTs stripped (`logging.py` lines 38–65). Render keeps that stdout. This review could not see whether Render has `SENTRY_DSN` set.

**Risk.** A scan exception or a 500 is a log line on a free service that sleeps. Nobody is paged.

**Fix.** Set `SENTRY_DSN` on the Frankfurt service, or a weekly look at Render logs. Keep the redacting `before_send` hook.

## What is already in good shape

These were checked and held up. They are the reason the list above is not longer.

- Passwords are Argon2 hashes. Production refuses the placeholder `SECRET_KEY` (`config.py` lines 168–182). JWTs are HS256 with the algorithm pinned. The role in the token is not trusted: `require_admin` re-reads `users.role`.
- Login of an unknown email still runs a dummy Argon2 check. Failed logins lock the row in the database. Password reset links carry `token_version` and a successful reset bumps it, which kills other sessions (`routes_auth.py` lines 364–382). Reset tokens are omitted from the JSON body when `ENV=production`.
- CV, generated-document, and cover-letter downloads check `user_id` and answer 404 for everyone else. Admin routes that were read (`/admin/dashboard`, `/admin/users`, scan, import, schedule, vacancy reports) depend on `require_admin`. Live unauthenticated calls to `/api/v1/companies` and `/api/v1/admin/dashboard` returned 401.
- SQL is SQLAlchemy queries. Company search escapes `%` and `_` (`routes_companies.py` lines 125–129). The `text()` calls in `session.py` are fixed DDL strings, not user input.
- The vacancy scraper blocks private and metadata addresses on each redirect. API responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, HSTS, and `Content-Security-Policy: default-src 'none'` (`main.py` lines 127–141). The live API responses included those headers. HSTS on the Vercel site is `max-age=63072000; includeSubDomains; preload`.
- Mock payment webhooks are rejected when `ENV=production` (`backend/app/payments/mock.py` lines 31–37). `render.yaml` still sets `PAYMENT_PROVIDER=mock`, so card checkout stays off until Paystack is configured. That is safe and it means donations by card do not work.
- Advertiser links are restricted to `http`/`https` in the browser (`frontend/src/lib/explorer/adSlots.ts` lines 100–105) and on the server (`backend/app/schemas/ad.py` lines 60–72).
- Account deletion bumps `token_version`, anonymises the email, and deletes stored CV bytes.
- `.env` is gitignored. History search for AWS keys, private keys, GitHub tokens, Brevo keys, and live Paystack keys found none.

## What this review did not do

- No password spraying, no secret guessing, no vulnerability scanner against production.
- No look at the Render or Vercel environment screens, Neon backups, or GitHub secret *values*.
- No confirmation of classic branch protection (the token was forbidden from reading it).
- No re-run of the full pytest access-control matrix. The route dependencies were read; they were not executed as a second user in this pass.

## Suggested order of work

1. H1 and H2 together: unverified accounts cannot do anything, Google sign-in still asks for TOTP when it is on, and admins cannot sign in until TOTP is on.
2. H3: put `assert_safe_fetch_url` on every redirect in the URL tester, the content hasher, and the icon job.
3. H4: Dependabot, secret scanning, and a required check on `main`. Confirm branch protection in the GitHub UI.
4. M5: bump `orjson`, `PyJWT`, `pypdf`, and Next.js, and add `pip-audit` to CI.
5. M2 and M3: parser caps, a storage quota, a complete export, and a delete path that Google-only users can finish.
6. M1 when you are ready for a cookie change: HttpOnly refresh token, rotation, then an enforcing CSP.
